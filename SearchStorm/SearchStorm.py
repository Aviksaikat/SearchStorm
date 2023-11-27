import argparse
import concurrent.futures
import os
import re

from click import style
from columnar import columnar
from termcolor import colored

# from prettytable import PrettyTable
# def print_result(result):
#     table = PrettyTable(["\033[32mLine No.\033[0m", "\033[32mLine Content\033[0m", "\033[32mFile Name\033[0m", "\033[32mPattern\033[0m"])
#     for match in result:
#         table.add_row([match[0], match[1], match[2], match[3].pattern])
#     print(table)


def highlight_pattern(text, pattern):
    start = text.find(pattern)
    highlighted = text[start : start + len(pattern)]
    new_text = (
        text[:start] + style(highlighted, fg="blue") + text[start + len(pattern) :]
    )
    # print(new_text)
    return new_text


def print_result(result, pattern):
    headers = ["Pattern ✨", " Line No. 🔧", "Line Content 🍑", "File Name 🎃"]
    # print(result[-1])
    # print(pattern)
    patterns = [
        ("Pattern", lambda text: style(text, fg="green")),
        (" Line No.", lambda text: style(text, fg="cyan")),
        ("Line Content", lambda text: style(text, fg="green")),
        ("File Name", lambda text: style(text, fg="blue")),
        (pattern, lambda text: style(text, fg="red")),
        ("/[a-zA-z]+/", lambda text: style(text, fg="yellow")),
        ("\d+", lambda text: style(text, fg="bright_green")),
        (f"{pattern}.*", lambda text: style(text, fg="black")),
    ]

    data = [
        [match[3], match[0], highlight_pattern(match[1], pattern), match[2]]
        for match in result
    ]
    # print(result[0][1])

    table = columnar(
        data, headers, patterns=patterns, justify="c", wrap_max=5, max_column_width=None
    )
    print(table)


def is_pattern_escaped(pattern):
    # print(pattern)
    for i in range(len(pattern)):
        if pattern[i] in "\\.\\*\\+\\?\\{\\}\\[\\]\\(\\)\\|\\^\\$\\":
            if i == 0 or pattern[i - 1] != "\\":
                return False
    return True


def escape_regex_special_chars(string):
    return re.escape(string)


def search_file(file_path, pattern, original_pattern):
    result = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.readlines()
        for i, line in enumerate(content):
            if pattern.search(line):
                result.append((i, line.strip(), file_path, original_pattern))
    return result


def search_files(directory, pattern, file_extension, scope_file=None):
    result = []

    original_pattern = pattern
    pattern = (
        escape_regex_special_chars(pattern) if is_pattern_escaped(pattern) else pattern
    )
    # print(pattern)
    pattern = re.compile(pattern, re.IGNORECASE)

    files_to_search = []
    if scope_file:
        with open(scope_file) as f:
            files_to_search = [line.strip() for line in f]
    else:
        for root, dir, files in os.walk(directory):
            files_to_search.extend(
                [os.path.join(root, f) for f in files if f.endswith(file_extension)]
            )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(search_file, f, pattern, original_pattern): f
            for f in files_to_search
        }
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result.extend(future.result())
            except Exception as e:
                print(f"Error processing file {file}: {e}")
    return result


def _print(result, pattern):
    if result:
        # print("---------| -------------------------- | -------------------------- | -------------------------- ")
        # for line_number, line, file, pattern in result:
        #     print(f"Line: {line_number} | Line Content: {line} | File: {file} | Pattern: {pattern}")
        print_result(result, pattern)
    else:
        print(colored("No match found", "red"))


def print_lines(result, directory):
    for i in range(len(result)):
        line_number = result[i][0] + 1
        file_name = result[i][-2]
        # print(file_name)
        remote_url = (
            subprocess.run(
                ["git", "-C", directory, "remote", "get-url", "origin"],
                stdout=subprocess.PIPE,
                text=True,
            )
            .stdout.replace("\n", "")
            .replace(".git", "")
        )
        print(
            str(remote_url)
            + "/"
            + "blob/main/"
            + str(file_name)
            + "#L"
            + str(line_number)
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search for pattern in files recursively"
    )
    parser.add_argument("-d", "--directory", required=True, help="Directory to search")
    parser.add_argument("-p", "--pattern", required=True, help="Pattern to search")
    parser.add_argument(
        "-e", "--extension", help="File extension to search (default: all files)"
    )
    args = parser.parse_args()

    # pattern = escape_regex_special_chars(args.pattern)
    result = search_files(args.directory, args.pattern, args.extension)

    _print(result, args.pattern)

    print("Lines: ")
    print_lines(result, args.directory)
