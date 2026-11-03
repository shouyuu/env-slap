#!/usr/bin/env python3
"""
env-slap: A hostile pre-commit hook to prevent accidental secret leaks 
and unmaintainable monolithic code blocks.
"""
import re
import sys
import subprocess

MAX_ALLOWED_LINES = 1500

# 탐지할 주요 시크릿 패턴 (OpenAI, AWS, GitHub 토큰, 일반적인 민감 키워드)
SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "OpenAI API Key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"-----BEGIN (RSA|PRIVATE) KEY-----"), "Private Key Block"),
]

def get_staged_files() -> list[str]:
    """git 커밋 대상(staged)으로 올라간 파일 목록을 가져옴"""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def get_file_content(filepath: str) -> str:
    """현재 스테이징된 파일의 내용을 가져옴"""
    result = subprocess.run(
        ["git", "show", f":{filepath}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="ignore"
    )
    return result.stdout

def main():
    staged_files = get_staged_files()
    violations = []

    print("[env-slap] Checking staged files for code hygiene violations...")

    for filepath in staged_files:
        # 1. .env 파일 차단 (.env.example 은 허용)
        if ".env" in filepath and not filepath.endswith(".example"):
            violations.append(f"  ❌ Blocked: '{filepath}' looks like an environment config file.")
            continue

        content = get_file_content(filepath)
        lines = content.splitlines()

        # 2. 1,500줄 초과 파일 차단 (단일 파일 비대화 방지)
        if len(lines) > MAX_ALLOWED_LINES:
            violations.append(
                f"  ❌ Blocked: '{filepath}' has {len(lines)} lines "
                f"(Exceeds limit of {MAX_ALLOWED_LINES} lines. Refactor your code)."
            )

        # 3. 코드 내 하드코딩된 시크릿 패턴 검사
        for idx, line in enumerate(lines, 1):
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        f"  ❌ Security Hazard: {label} detected in '{filepath}' at line {idx}."
                    )

    if violations:
        print("\n[env-slap] 🚨 Commit rejected due to the following violations:\n")
        for v in violations:
            print(v)
        print("\nFix these issues before committing, or use --no-verify at your own risk.\n")
        sys.exit(1)

    print("[env-slap] ✨ Code hygiene check passed. Proceeding with commit.")
    sys.exit(0)

if __name__ == "__main__":
    main()