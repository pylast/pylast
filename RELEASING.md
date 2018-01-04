# Release Checklist

* [ ] Get master to the appropriate code release state. [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Remove `.dev0` suffix from version in `pylast/__init__.py` and `setup.py`:
```bash
git checkout master
edit pylast/__init__.py setup.py
```
* [ ] Commit and tag with the version number:
```bash
git add pylast/__init__.py setup.py
git commit -m "Release 2.1.0"
git tag -a 2.1.0 -m "Release 2.1.0"
```
* [ ] Create a distribution and release on PyPI:
```bash
pip install -U pip setuptools wheel twine keyring
rm -rf build
python setup.py sdist --format=gztar bdist_wheel
twine upload -r pypi dist/pylast-2.1.0*
```
* [ ] Check installation: `pip install -U pylast`
* [ ] Push commits and tags:
 ```bash
git push
git push --tags
```
* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
  * Tag: Pick existing tag "2.1.0"
  * Title: "Release 2.1.0"
* [ ] Increment version and append `.dev0` in `pylast/__init__.py` and `setup.py`:
```bash
git checkout master
edit pylast/__init__.py setup.py
```
* [ ] Commit and push:
```bash
git add pylast/__init__.py setup.py
git commit -m "Start new release cycle"
git push
```
