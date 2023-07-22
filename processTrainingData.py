import os
import json
import subprocess
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace

def create_tokenizer(pd_files_data):
    tokenizer = Tokenizer(BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    trainer = BpeTrainer(special_tokens=["[UNK]"], vocab_size=50000)
    tokenizer.train_from_iterator(pd_files_data, trainer)
    return tokenizer

def save_to_jsonl(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        for idx, item in enumerate(data):
            prompt, completion = item.split("\n\n", 1)
            json_obj = {"prompt": prompt, "completion": completion}
            file.write(json.dumps(json_obj, ensure_ascii=False))
            file.write("\n")

def read_pd_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def clean_content(content):
    content = content.replace("\t", " ").replace("\r", "").strip()
    lines = content.split("\n")
    cleaned_lines = [line.strip() for line in lines]
    cleaned_content = "\n".join(cleaned_lines)
    return cleaned_content

def process_pd_files(folder_path, tokenizer, max_tokens):
    data = []
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isdir(file_path):
            data.extend(process_pd_files(file_path, tokenizer, max_tokens))
        elif file.endswith(".pd"):
            content = read_pd_file(file_path)
            cleaned_content = clean_content(content)
            title_and_content = f"PureData Patch: {file[:-3]}\n\n {cleaned_content}\n"

            lines = title_and_content.split("\n")
            truncated_lines = []
            tokens_so_far = 0

            if tokenizer is None:
                tokenizer = create_tokenizer(process_pd_files(folder_path, tokenizer=None, max_tokens=max_tokens))

            for line in lines:
                line_tokens = tokenizer.encode(line).tokens
                if tokens_so_far + len(line_tokens) < max_tokens:
                    truncated_lines.append(line)
                    tokens_so_far += len(line_tokens)
                else:
                    truncated_lines = []
                    break

            truncated_text = "\n".join(truncated_lines)

            if truncated_text:
                data.append(truncated_text)
    return data

def prepare_pd_files_data(folder_path, max_tokens):
    pd_files_data = []
    for file in os.listdir(folder_path):
        if file.endswith(".pd"):
            file_path = os.path.join(folder_path, file)
            content = read_pd_file(file_path)
            cleaned_content = clean_content(content)
            title_and_content = f"PureData Patch: {file[:-3]}\n\n {cleaned_content}\n"
            pd_files_data.append(title_and_content)

    tokenizer = create_tokenizer(pd_files_data)
    return tokenizer, pd_files_data

def main():
    folder_path = "/Users/macuser/Documents/GitHub/PureDataGPT/TrainingData"
    output_file = "pd_files.jsonl"
    max_tokens = 2048

    tokenizer, pd_files_data = prepare_pd_files_data(folder_path, max_tokens)
    data = process_pd_files(folder_path, tokenizer, max_tokens)
    save_to_jsonl(data, output_file)

    # Call the CLI tool to prepare the data
    prepare_data_command = f"openai tools fine_tunes.prepare_data -f {output_file}"
    subprocess.run(prepare_data_command, shell=True, check=True)

if __name__ == "__main__":
    main()
