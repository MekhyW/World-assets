import argparse
import json
import sys
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
import higgsfield_client
from higgsfield_client.exceptions import CredentialsMissedError, HiggsfieldClientError


def parse_value(val: str):
    """Attempt to parse a string as JSON (int, float, bool, dict, list), fallback to str."""
    try:
        return json.loads(val)
    except Exception:
        return val


def parse_kv(arg_str: str) -> tuple[str, any]:
    """Parse KEY=VALUE into a tuple, converting value type if possible."""
    if "=" not in arg_str:
        raise ValueError(f"Argument must be in KEY=VALUE format, got: {arg_str!r}")
    key, val = arg_str.split("=", 1)
    return key.strip(), parse_value(val.strip())


def parse_extra_cli_args(extra_args: list[str]) -> dict:
    """Parse arbitrary leftover CLI flags (--key value, --key=value, --bool-flag)."""
    extras = {}
    i = 0
    while i < len(extra_args):
        arg = extra_args[i]
        if arg.startswith("--"):
            key_part = arg[2:]
            if "=" in key_part:
                k, v = key_part.split("=", 1)
                extras[k.replace("-", "_")] = parse_value(v)
                i += 1
            else:
                k = key_part.replace("-", "_")
                if i + 1 < len(extra_args):
                    nxt = extra_args[i + 1]
                    is_numeric = nxt.lstrip("-").replace(".", "", 1).isdigit()
                    if not nxt.startswith("-") or is_numeric:
                        extras[k] = parse_value(nxt)
                        i += 2
                        continue
                extras[k] = True
                i += 1
        else:
            i += 1
    return extras


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agnostic CLI tool to run generations with Higgsfield models.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", "--model", default=None, help="Higgsfield model identifier (e.g. bytedance/seedance-2.5/text-to-video)",)
    parser.add_argument("-p", "--prompt", default=None, help="Prompt text for generation. Pass '-' to read from standard input.")
    parser.add_argument("--prompt-file", type=Path, default=None, help="Path to a text file containing the prompt.")
    parser.add_argument("-d", "--duration", type=int, default=None, help="Duration of the generated video in seconds.")
    parser.add_argument("-a", "--aspect-ratio", default=None, help="Aspect ratio (e.g. 9:16, 16:9, 1:1, 4:3).")
    parser.add_argument("-r", "--resolution", default=None, help="Resolution tier (e.g. 480p, 720p, 1080p).")
    parser.add_argument("--negative-prompt", default=None, help="Negative prompt text describing elements to exclude.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for generation.")
    parser.add_argument("--image-url", default=None, help="Input image URL for image-to-video or reference inputs.")
    parser.add_argument("-e", "--arg", dest="extra_args", action="append", default=[], metavar="KEY=VALUE", help="Arbitrary model argument in KEY=VALUE format. Can be used multiple times.")
    parser.add_argument("--args-json", default=None, help="Raw JSON string of model arguments.")
    parser.add_argument("--args-file", type=Path, default=None, help="Path to a JSON file containing model arguments.")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Path to save / download the generated media output.")
    parser.add_argument("--json", action="store_true", help="Output full API response as JSON to stdout.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress updates and informational messages.")
    parser.add_argument("--env-file", type=Path, default=None, help="Path to .env file to load HF_KEY credentials from.")
    return parser


def load_environment(env_file: Path | None = None) -> None:
    if env_file:
        load_dotenv(env_file, override=False)
        return
    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()
    for candidate in [cwd / ".env.local", cwd / ".env", script_dir / ".env.local", script_dir / ".env"]:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            break


def extract_media_url(result: dict) -> str | None:
    video_obj = result.get("video")
    if isinstance(video_obj, dict) and video_obj.get("url"):
        return video_obj["url"]
    images = result.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict) and first.get("url"):
            return first["url"]
        if isinstance(first, str):
            return first
    for field in ("url", "output", "image"):
        val = result.get(field)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict) and val.get("url"):
            return val["url"]
    return None


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    load_environment(args.env_file)
    # 1. Start with arguments from file if provided
    arguments = {}
    if args.args_file:
        if not args.args_file.is_file():
            print(f"ERROR: Arguments file not found: {args.args_file}", file=sys.stderr)
            return 1
        with open(args.args_file, "r", encoding="utf-8") as f:
            arguments.update(json.load(f))
    # 2. Merge arguments from JSON string
    if args.args_json:
        try:
            arguments.update(json.loads(args.args_json))
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid JSON in --args-json: {exc}", file=sys.stderr)
            return 1
    # 3. Merge unknown CLI flags (--foo bar, --bool-flag)
    if unknown:
        arguments.update(parse_extra_cli_args(unknown))
    # 4. Merge -e / --arg KEY=VALUE
    for kv in args.extra_args:
        try:
            k, v = parse_kv(kv)
            arguments[k] = v
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    # 5. Apply explicit CLI options
    if args.duration is not None:
        arguments["duration"] = args.duration
    if args.aspect_ratio is not None:
        arguments["aspect_ratio"] = args.aspect_ratio
    if args.resolution is not None:
        arguments["resolution"] = args.resolution
    if args.negative_prompt is not None:
        arguments["negative_prompt"] = args.negative_prompt
    if args.seed is not None:
        arguments["seed"] = args.seed
    if args.image_url is not None:
        arguments["image_url"] = args.image_url
    # Model resolution and validation
    model = args.model or arguments.pop("model", None)
    if not model:
        print("ERROR: Model is required. Specify via --model / -m or in arguments file/JSON.", file=sys.stderr)
        return 2
    # Prompt resolution and validation
    prompt = None
    if args.prompt == "-":
        prompt = sys.stdin.read().strip()
    elif args.prompt is not None:
        prompt = args.prompt
    elif args.prompt_file is not None:
        if not args.prompt_file.is_file():
            print(f"ERROR: Prompt file not found: {args.prompt_file}", file=sys.stderr)
            return 1
        prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    if prompt is not None:
        arguments["prompt"] = prompt
    if not arguments.get("prompt"):
        print("ERROR: Prompt is required. Specify via --prompt / -p, --prompt-file, or in arguments file/JSON.", file=sys.stderr)
        return 2
    # Logging output stream: if --json is requested, send logs to stderr
    log_stream = sys.stderr if args.json else sys.stdout
    def log(msg: str) -> None:
        if not args.quiet:
            print(msg, file=log_stream, flush=True)
    summary_parts = [f"{k}={v!r}" for k, v in arguments.items() if k != "prompt"]
    summary_str = f" ({', '.join(summary_parts)})" if summary_parts else ""
    log(f"Submitting {model}{summary_str}...")
    def on_status(status) -> None:
        log(f"  status: {type(status).__name__}")
    try:
        result = higgsfield_client.subscribe(model, arguments=arguments, on_enqueue=lambda request_id: log(f"request_id: {request_id}"), on_queue_update=on_status)
    except CredentialsMissedError:
        print("ERROR: HF_KEY is not set. Add HF_KEY=<key-id>:<key-secret> to .env.local or environment.", file=sys.stderr)
        return 2
    except HiggsfieldClientError as exc:
        print(f"ERROR: Higgsfield API request failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    status = result.get("status")
    request_id = result.get("request_id")
    if status == "completed":
        url = extract_media_url(result)
        if url:
            if not args.json:
                log("SUCCESS: generation completed")
                print(url)
            if args.output:
                log(f"Downloading to {args.output}...")
                try:
                    download_file(url, args.output)
                    log(f"Saved media to {args.output}")
                except Exception as exc:
                    print(f"ERROR: Failed to download media: {exc}", file=sys.stderr)
                    return 1
            return 0
        print(f"ERROR: request {request_id} completed but returned no media URL: {result}", file=sys.stderr)
        return 1
    reasons = {
        "nsfw": "was blocked by content moderation (nsfw)",
        "failed": "failed during generation",
        "canceled": "was canceled",
    }
    reason = reasons.get(status, f"ended with unexpected status {status!r}")
    print(f"ERROR: request {request_id} {reason}. No media was produced.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
