# Release Checklist

* [ ] Get [master to the appropriate code release state](https://github.com/pylast/pylast/compare/master...develop?expand=1&title=Merge%20develop%20into%20master). [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Remove `.dev0` suffix from version in `pylast/__init__.py` and `setup.py` and commit:
```bash
git checkout master
edit pylast/__init__.py setup.py
git add pylast/__init__.py setup.py
git commit -m "Release 2.0.0"
```
* [ ] Tag the last commit with the version number:
```bash
git tag -a 2.0.0 -m "Release 2.0.0"
```
* [ ] Create a distribution and release on PyPI:
```bash
pip install -U pip setuptools wheel twine keyring
rm -rf build
python setup.py sdist --format=gztar bdist_wheel
twine upload -r pypi dist/pylast-2.0.0*
```
* [ ] Check installation: `pip install -U pylast`
* [ ] Push: `git push`
* [ ] Push tags: `git push --tags`
* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
  * Tag: Pick existing tag "2.0.0"
  * Title: "Release 2.0.0"
* [ ] Increment version and append `.dev0` in `pylast/__init__.py` and `setup.py` and commit:
```bash
git checkout master
edit pylast/__init__.py setup.py
git add pylast/__init__.py setup.py
git commit -m "Start new release cycle"
git push
```
* [ ] Update develop branch from master:
```bash
git checkout develop
git merge master --ff-only
git push
```
