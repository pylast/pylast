#!/usr/bin/env bash
clonedigger pylast
grep -E "Clones detected|lines are duplicates" output.html
exit 0
