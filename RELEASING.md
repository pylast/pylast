# Release Checklist

* [ ] Get [master to the appropriate code release state](https://github.com/pylast/pylast/compare/master...develop?expand=1). [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Update version in `pylast/__init__.py` and `setup.py` and commit:
```bash
git checkout master
edit pylast/__init__.py setup.py
git add pylast/__init__.py setup.py
git commit -m "Release 1.8.0"
```
* [ ] Tag the last commit with the version number:
```bash
git tag -a 1.8.0 -m "Release 1.8.0"
```
* [ ] Release on PyPI:
```bash
twine upload dist/pylast-1.8.0.tar.gz
```
* [ ] Check installation: `pip install -U pylast`
* [ ] Push: `git push`
* [ ] Push tags: `git push --tags`
* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
  * Tag: Pick existing tag "1.8.0" 
  * Title: "Release 1.8.0"
* [ ] Update develop branch from master:
```bash
git checkout develop
git merge master --ff-only
git push
```
