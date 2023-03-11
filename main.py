# !/usr/bin/env python3
# coding=utf-8
from __future__ import annotations

import json
import time
from typing import Any, Generator

import ftfy
import openai

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def chapter_to_str(chapter):
    soup = BeautifulSoup(chapter.get_body_content(), "html.parser")
    text = [para.get_text() for para in soup.find_all("p")]
    return "\n".join(text)


def clip_chunk(raw_text: str) -> str:
    text = raw_text.strip()
    len_text = len(text)
    if len_text < 1:
        return text

    start = 0
    end = len_text

    # remove partial sentences at the beginning
    while start < end:
        if text[start] in {".", "!", "?"}:
            start += 1
            break
        start += 1

    # remove partial sentences at the end
    while end > start:
        if text[end - 1] in {".", "!", "?"}:
            break
        end -= 1

    return text[start:end].strip()


def read_epub(file_name: str) -> str:
    book = epub.read_epub(file_name)

    started = False
    text = ""
    for item in book.get_items():
        if item.get_type() not in {ebooklib.ITEM_DOCUMENT}:
            continue

        if not started:
            if item.id == "intro":
                started = True
            else:
                continue

        chapter = chapter_to_str(item)
        text += chapter
    return text


def generate_chunks(file_name: str, chunk_size: int = 3000, overlap: int = 400) -> Generator[str, None, None]:
    if file_name.endswith(".epub"):
        text = read_epub(file_name)
    elif file_name.endswith(".txt"):
        with open(file_name, mode="r", encoding="utf-8") as f:
            text = f.read()
    len_text = len(text)
    chunk_overlap_start = overlap
    chunk_overlap_end = overlap
    for i in range(0, len_text - chunk_size, chunk_size):
        chunk_start = max(0, i - chunk_overlap_start)
        chunk_end = min(len_text, i + chunk_size + chunk_overlap_end)
        text_chunk = text[chunk_start:chunk_end]
        yield clip_chunk(text_chunk)


def main() -> None:
    file_name = r"D:\Dropbox\Bücher\efficiency\Tiago Forte - Building a Second Brain _ A Proven Method to Organize Your Digital Life and Unlock Your Creative Potential (2022, " \
                r"Atria Books) - libgen.li.epub"

    file_name = r"resources/summary_02.txt"

    summary_file = "resources/summary.txt"
    with open("resources/config.json", mode="r") as f:
        config = json.load(f)

    openai.api_key = config["openai_secret"]
    openai.organization = config["organization_id"]
    parameters: dict[str, Any] = config["parameters"]

    messages = parameters.pop("messages")
    history = list()
    chunk_size = 3000
    summary_size = chunk_size // 10

    chunks = list(generate_chunks(file_name, chunk_size=chunk_size))
    summary = ""
    for n, chunk in enumerate(chunks):
        print(f"chunk {n+1:d} of {len(chunks):d}")
        text = f"Text passage:\n{chunk}"
        if n >= 1:
            text = f"Preface:\n{summary:s}\n\n" + text
        instruction = f"{text:s}\n\nSummarize the interesting, novel, or unique aspects from the above text passage in about {summary_size:d} characters."
        if n >= 1:
            instruction += " Write the summary as a natural continuation of the preface above. Don't start with the exact same words. When necessary, use terms from the preface " \
                           "instead of introducing new ones."

        print(instruction)
        history.append({
            "role": "user",
            "content": instruction,
          })

        # parameters: https://platform.openai.com/docs/api-reference/chat/create
        response = openai.ChatCompletion.create(
            **parameters,
            messages=messages + history,
        )

        history.clear()

        first_choice = response["choices"][0]
        reply: str = first_choice["message"]["content"]
        finish_reason = first_choice["finish_reason"]

        summary = ftfy.fix_encoding(reply)
        try:
            output = f"summary: {summary:s} (fr: {str(finish_reason):s})"
        except TypeError as e:
            raise e
        print(output)

        with open(summary_file, mode="a", encoding="utf-8") as f:
            # f.write(instruction + "\n\n")
            f.write(summary + "\n\n")

        print("sleeping for 1 second...")
        time.sleep(1)


if __name__ == "__main__":
    main()
