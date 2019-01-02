# Release Checklist
* [ ] Get master to the appropriate code release state. [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Remove `.dev0` suffix from the version and update version and date in the changelog:
```bash
git checkout master
edit pylast/version.py
edit CHANGELOG.md
```
* [ ] Commit and tag with the version number:
```bash
git add CHANGELOG.md pylast/version.py
git commit -m "Release 3.0.0"
git tag -a 3.0.0 -m "Release 3.0.0"
```
* [ ] Create a distribution and release on PyPI:
```bash
pip3 install -U pip setuptools wheel twine keyring
rm -rf build
python3 setup.py sdist --format=gztar bdist_wheel
twine check dist/*
twine upload -r pypi dist/pylast-3.0.0*
```
* [ ] Check installation: `pip3 uninstall -y pylast && pip3 install -U pylast`
* [ ] Push commits and tags:
 ```bash
git push
git push --tags
```
* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
  * Tag: Pick existing tag "3.0.0"
  * Title: "Release 3.0.0"
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
