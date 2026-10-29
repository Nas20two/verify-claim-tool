#!/usr/bin/env python3
"""verify-claim — Agent claim verification tool
PAIN #1: verify agent completion claims before reporting "done"

Usage:
  verify-claim commit --sha <sha> --branch <branch> [--repo <path>]
  verify-claim file --path <path> [--sha256 <expected>]
  verify-claim deploy --url <url> [--expect-status <code>] [--expect-body-sha256 <hash>]
  verify-claim build --artifact <path>

Flags:
  --audit       Kai-side mode: stricter checks, verbose evidence
  --format json Machine-readable JSON output
  -q, --quiet   Silent mode: exit code only

Exit codes:
  0 = PASS (claim verified)
  1 = FAIL (claim could not be verified)
  2 = USAGE (invalid arguments)
"""

import argparse
import json
import os
import subprocess
import sys
import hashlib
import shutil
from urllib.request import urlopen, Request
from urllib.error import URLError

VERSION = "0.1.0"


def json_escape(s):
    return json.dumps(s)


def emit_json(status, claim_type, evidence):
    output = {
        "status": status,
        "claim_type": claim_type,
        "version": VERSION,
        "evidence": evidence,
    }
    print(json.dumps(output, indent=2))


def log_pass(msg, quiet, fmt):
    if quiet or fmt == "json":
        return
    print(f"\033[0;32m✓ PASS:\033[0m {msg}")


def log_fail(msg, quiet, fmt):
    if quiet or fmt == "json":
        return
    print(f"\033[0;31m✗ FAIL:\033[0m {msg}", file=sys.stderr)


def log_info(msg, quiet, fmt):
    if quiet or fmt == "json":
        return
    print(f"\033[0;36mℹ\033[0m {msg}")


def log_detail(msg, quiet, fmt):
    if quiet or fmt == "json":
        return
    print(f"  {msg}")


def verify_commit(args, quiet, fmt, audit):
    sha = args.sha
    branch = args.branch
    repo = args.repo or "."

    log_info(f"Verifying commit {sha} on branch '{branch}' in repo '{repo}'", quiet, fmt)

    git_dir = os.path.join(repo, ".git")
    if not os.path.isdir(git_dir):
        log_fail(f"Not a git repository: {repo}", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", {"sha": sha, "branch": branch, "repo": repo, "error": "Not a git repository"})
        return 1

    # Get remote URL
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        log_fail("No remote 'origin' configured", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", {"sha": sha, "branch": branch, "repo": repo, "error": "No remote origin"})
        return 1

    remote_url = result.stdout.strip()
    log_detail(f"Remote URL: {remote_url}", quiet, fmt)

    # Run git ls-remote
    ref = f"refs/heads/{branch}"
    log_detail(f"Running: git ls-remote origin {ref}", quiet, fmt)

    result = subprocess.run(
        ["git", "ls-remote", "origin", ref],
        cwd=repo, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        log_fail(f"git ls-remote failed (exit {result.returncode})", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", {"sha": sha, "branch": branch, "repo": repo, "error": f"ls-remote failed: {result.stderr.strip()}"})
        return 1

    ls_remote_output = result.stdout.strip()
    if not ls_remote_output:
        log_fail(f"Branch '{branch}' not found on origin", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", {"sha": sha, "branch": branch, "repo": repo, "error": "Branch not found on origin"})
        return 1

    lines = ls_remote_output.split("\n")
    remote_sha = lines[0].split()[0] if lines else ""
    log_detail(f"Remote HEAD: {remote_sha}", quiet, fmt)

    sha_found = sha in ls_remote_output or remote_sha == sha

    if not sha_found and audit:
        log_detail("Audit: fetching and checking ancestry...", quiet, fmt)
        subprocess.run(
            ["git", "fetch", "origin", branch],
            cwd=repo, capture_output=True, timeout=60
        )
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, f"origin/{branch}"],
            cwd=repo, capture_output=True, timeout=30
        )
        if result.returncode == 0:
            sha_found = True

    evidence = {
        "sha": sha,
        "branch": branch,
        "repo": repo,
        "remote_url": remote_url,
        "remote_head": remote_sha,
        "ls_remote_output": ls_remote_output,
    }

    if sha_found:
        log_pass(f"Commit {sha} found on origin/{branch}", quiet, fmt)
        if fmt == "json":
            emit_json("PASS", "commit", evidence)
        return 0
    else:
        log_fail(f"Commit {sha} NOT found on origin/{branch}", quiet, fmt)
        log_detail("The claimed commit does not exist on the remote.", quiet, fmt)
        log_detail("The agent likely committed locally but never pushed.", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", evidence)
        return 1


def verify_file(args, quiet, fmt):
    path = args.path
    expected_sha256 = args.sha256

    log_info(f"Verifying file: {path}", quiet, fmt)

    if not os.path.exists(path):
        log_fail(f"File does not exist: {path}", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "file", {"path": path, "exists": False, "error": "File not found"})
        return 1

    # Calculate SHA256
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    actual_sha256 = sha256_hash.hexdigest()

    try:
        file_size = os.path.getsize(path)
    except OSError:
        file_size = "unknown"

    log_detail(f"SHA256: {actual_sha256}", quiet, fmt)
    log_detail(f"Size: {file_size} bytes", quiet, fmt)

    evidence = {
        "path": path,
        "exists": True,
        "sha256": actual_sha256,
        "size": file_size,
    }

    if expected_sha256:
        evidence["expected_sha256"] = expected_sha256
        if actual_sha256 != expected_sha256:
            log_fail(f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}", quiet, fmt)
            if fmt == "json":
                emit_json("FAIL", "file", evidence)
            return 1
        log_pass("SHA256 matches expected checksum", quiet, fmt)

    log_pass(f"File exists at {path}", quiet, fmt)
    if fmt == "json":
        emit_json("PASS", "file", evidence)
    return 0


def verify_deploy(args, quiet, fmt):
    url = args.url
    expect_status = args.expect_status or 200
    expect_body_sha256 = args.expect_body_sha256

    log_info(f"Verifying deployment: {url}", quiet, fmt)
    log_detail(f"Expected status: {expect_status}", quiet, fmt)

    try:
        req = Request(url, method="HEAD")
        resp = urlopen(req, timeout=10)
        http_status = resp.status
    except URLError as e:
        http_status = 0
    except Exception:
        http_status = 0

    log_detail(f"HTTP status: {http_status}", quiet, fmt)

    if http_status != expect_status:
        log_fail(f"HTTP status mismatch: expected {expect_status}, got {http_status}", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "deploy", {"url": url, "http_status": http_status, "expected_status": expect_status})
        return 1

    log_pass(f"HTTP {http_status} — URL is reachable", quiet, fmt)

    if expect_body_sha256:
        try:
            req = Request(url)
            resp = urlopen(req, timeout=10)
            body = resp.read()
            body_sha256 = hashlib.sha256(body).hexdigest()
            log_detail(f"Body SHA256: {body_sha256}", quiet, fmt)

            if body_sha256 != expect_body_sha256:
                log_fail("Body SHA256 mismatch", quiet, fmt)
                if fmt == "json":
                    emit_json("FAIL", "deploy", {"url": url, "http_status": http_status, "body_sha256": body_sha256, "expected_body_sha256": expect_body_sha256})
                return 1
            log_pass("Body SHA256 matches expected", quiet, fmt)
        except Exception as e:
            log_fail(f"Could not fetch body: {e}", quiet, fmt)
            if fmt == "json":
                emit_json("FAIL", "deploy", {"url": url, "http_status": http_status, "error": str(e)})
            return 1

    log_pass(f"Deployment at {url} is serving expected content", quiet, fmt)
    if fmt == "json":
        emit_json("PASS", "deploy", {"url": url, "http_status": http_status})
    return 0


def verify_build(args, quiet, fmt):
    artifact = args.artifact

    log_info(f"Verifying build artifact: {artifact}", quiet, fmt)

    if not os.path.exists(artifact):
        log_fail(f"Build artifact does not exist: {artifact}", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "build", {"artifact": artifact, "exists": False, "error": "Artifact not found"})
        return 1

    try:
        file_size = os.path.getsize(artifact)
    except OSError:
        file_size = "unknown"

    sha256_hash = hashlib.sha256()
    with open(artifact, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    sha256 = sha256_hash.hexdigest()

    log_detail(f"Size: {file_size} bytes", quiet, fmt)
    log_detail(f"SHA256: {sha256}", quiet, fmt)

    log_pass(f"Build artifact exists at {artifact} ({file_size} bytes)", quiet, fmt)
    if fmt == "json":
        emit_json("PASS", "build", {"artifact": artifact, "exists": True, "size": file_size, "sha256": sha256})
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Agent claim verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  verify-claim commit --sha abc123 --branch feature-x --repo /path/to/repo
  verify-claim file --path /path/to/file --sha256 d41d8cd98f...
  verify-claim deploy --url https://example.com --expect-status 200
  verify-claim build --artifact ./dist/bundle.js
        """,
    )
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Silent mode: exit code only")
    parser.add_argument("--audit", action="store_true", help="Kai-side mode: stricter checks, verbose evidence")

    subparsers = parser.add_subparsers(dest="claim_type", help="Claim type to verify")
    subparsers.required = True

    # Commit
    p_commit = subparsers.add_parser("commit", help="Verify a commit exists on origin")
    p_commit.add_argument("--sha", required=True, help="Claimed commit SHA")
    p_commit.add_argument("--branch", required=True, help="Branch name")
    p_commit.add_argument("--repo", default=".", help="Path to git repository (default: cwd)")

    # File
    p_file = subparsers.add_parser("file", help="Verify a file exists")
    p_file.add_argument("--path", required=True, help="File path")
    p_file.add_argument("--sha256", help="Expected SHA256 checksum")

    # Deploy
    p_deploy = subparsers.add_parser("deploy", help="Verify a deployment URL")
    p_deploy.add_argument("--url", required=True, help="Deployment URL")
    p_deploy.add_argument("--expect-status", type=int, default=200, help="Expected HTTP status code")
    p_deploy.add_argument("--expect-body-sha256", help="Expected body SHA256 checksum")

    # Build
    p_build = subparsers.add_parser("build", help="Verify a build artifact exists")
    p_build.add_argument("--artifact", required=True, help="Path to build artifact")

    args = parser.parse_args()
    quiet = args.quiet
    fmt = args.format

    if args.claim_type == "commit":
        sys.exit(verify_commit(args, quiet, fmt, args.audit))
    elif args.claim_type == "file":
        sys.exit(verify_file(args, quiet, fmt))
    elif args.claim_type == "deploy":
        sys.exit(verify_deploy(args, quiet, fmt))
    elif args.claim_type == "build":
        sys.exit(verify_build(args, quiet, fmt))


if __name__ == "__main__":
    main()
