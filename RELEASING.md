# Release Checklist

* [ ] Get master to the appropriate code release state. [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for all merges to master.
* [ ] Remove `.dev0` suffix from the version and update version and date in the changelog:
```bash
git checkout master
edit CHANGELOG.md src/pylast/version.py
```
* [ ] Commit and tag with the version number:
```bash
git add CHANGELOG.md src/pylast/version.py
git commit -m "Release 3.0.0"
git tag -a 3.0.0 -m "Release 3.0.0"
```

* [ ] Push commits and tags:
 ```bash
git push
git push --tags
```

* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new
  * Tag: Pick existing tag "3.0.0"
  * Title: "Release 3.0.0"

* [ ] Check the tagged [Travis CI build](https://travis-ci.org/pylast/pylast) has deployed to [PyPI](https://pypi.org/project/pylast/#history)

* [ ] Check installation: `pip3 uninstall -y pylast && pip3 install -U pylast`

* [ ] Increment version and append `.dev0`, and add Unreleased to the changelog:
```bash
git checkout master
edit CHANGELOG.md src/pylast/version.py
```
* [ ] Commit and push:
```bash
git add CHANGELOG.md src/pylast/version.py
git commit -m "Start new release cycle"
git push
```
