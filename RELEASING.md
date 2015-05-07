# Release Checklist

* [ ] Get master to the appropriate code release state. [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Update version in `pylast/__init__.py` and `setup.py` and commit:
```bash
git add pylast/__init__.py setup.py
git commit -m "Release 1.3.0"
```
* [ ] Tag the last commit with the version number:
```bash
git tag -a 1.3.0 -m "Release 1.3.0"
```
* [ ] Release on PyPI:
```bash
python setup.py register
python setup.py sdist --format=gztar upload
```
* [ ] Push: `git push`
* [ ] Push tags: `git push --tags`
* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
* [ ] Update develop branch from master:
```bash
git checkout develop
git merge master --ff-only
git push
```
