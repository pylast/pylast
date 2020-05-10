# Release Checklist

* [ ] Get master to the appropriate code release state.
      [Travis CI](https://travis-ci.org/pylast/pylast) should be running cleanly for
      all merges to master.

* [ ] Edit release draft, adjust text if needed:
      https://github.com/pylast/pylast/releases

* [ ] Check next tag is correct, amend if needed

* [ ] Copy text into [`CHANGELOG.md`](CHANGELOG.md)

* [ ] Publish release

* [ ] Check the tagged [Travis CI build](https://travis-ci.org/pylast/pylast) has
      deployed to [PyPI](https://pypi.org/project/pylast/#history)

* [ ] Check installation:

```bash
pip3 uninstall -y pylast && pip3 install -U pylast
```
