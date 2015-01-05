pyflakes pylast
echo ---
pyflakes tests
echo ---
pep8 pylast
echo ---
pep8 tests
# echo ---
# clonedigger pylast.py
# grep "Clones detected" output.html
# grep "lines are duplicates" output.html
