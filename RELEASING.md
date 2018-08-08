# Release Checklist

* [ ] Get master to the appropriate code release state. [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Remove `.dev0` suffix from the version:
```bash
git checkout master
edit pylast/version.py
```
* [ ] Commit and tag with the version number:
```bash
git add pylast/version.py
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
* [ ] Increment version and append `.dev0`:
```bash
git checkout master
edit pylast/version.py
```
* [ ] Commit and push:
```bash
git add pylast/version.py
git commit -m "Start new release cycle"
git push
```
