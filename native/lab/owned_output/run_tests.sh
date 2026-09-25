#!/bin/sh
set -eu

lab_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$lab_dir/build"
set -- -std=c11 -Wall -Wextra -Werror -pedantic -O2
if [ "${AQSS_LAB_SANITIZE:-0}" = 1 ]; then
    set -- "$@" -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined
fi
"${CC:-cc}" "$@" \
    "$lab_dir/owner.c" "$lab_dir/test_owner.c" \
    -o "$lab_dir/build/test_owner"
"$lab_dir/build/test_owner"
"${CC:-cc}" "$@" \
    "$lab_dir/owner.c" "$lab_dir/callbacks.c" "$lab_dir/test_callbacks.c" \
    -o "$lab_dir/build/test_callbacks"
"$lab_dir/build/test_callbacks"
