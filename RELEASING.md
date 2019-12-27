# Release Checklist

* [ ] Get master to the appropriate code release state.
      [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for
      all merges to master.

* [ ] Tag with the version number:

```bash
git tag -a 3.2.0 -m "Release 3.2.0"
```

* [ ] Push tag:

```bash
git push --tags
```

* [ ] Create new GitHub release: https://github.com/pylast/pylast/releases/new

  * Tag: Pick existing tag "3.2.0"

* [ ] Check the tagged [Travis CI build](https://travis-ci.org/pylast/pylast) has
      deployed to [PyPI](https://pypi.org/project/pylast/#history)

* [ ] Check installation:

```bash
pip3 uninstall -y pylast && pip3 install -U pylast
```
