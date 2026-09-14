# Lab 01 - Temporary File Cleanup

## Description

`cleanup.sh` is a Bash script that automates the process of deleting temporary files from a specified directory.

The script accepts the path to the directory as the first obligatory argument.

Additional arguments can be used to specify the file extensions that should be deleted.

If no extension is specified, the script deletes `.tmp` files by default.

At the end of execution, the script displays the total number of deleted files.

## Requirements

- Bash
- macOS, Linux, or another Unix-like operating system

No additional software installation is required.

## Usage

Basic syntax:

```bash
./cleanup.sh <directory> [extension1] [extension2] ...
