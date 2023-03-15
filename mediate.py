# !/usr/bin/env python3
# coding=utf-8
from __future__ import annotations

import json
import time
from typing import Any

import ftfy
import openai


def main() -> None:
    with open("resources/config_mediate.json", mode="r") as f:
        config = json.load(f)

    openai.api_key = config["openai_secret"]
    openai.organization = config["organization_id"]
    parameters: dict[str, Any] = config["parameters"]

    messages = parameters.pop("messages")
    history = list()

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
