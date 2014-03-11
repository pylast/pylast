pyflakes pylast.py
echo ---
pyflakes test_pylast.py
echo ---
pep8 test_pylast.py
echo ---
pep8 pylast.py
# echo ---
# clonedigger pylast.py
# grep "Clones detected" output.html
# grep "lines are duplicates" output.html
