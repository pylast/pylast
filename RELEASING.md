# Release checklist

- [ ] Get `main` to the appropriate code release state.
      [GitHub Actions](https://github.com/pylast/pylast/actions) should be running
      cleanly for all merges to `main`.
      [![Test](https://github.com/pylast/pylast/workflows/Test/badge.svg)](https://github.com/pylast/pylast/actions)

- [ ] Edit release draft, adjust text if needed:
      https://github.com/pylast/pylast/releases

- [ ] Check next tag is correct, amend if needed

- [ ] Publish release

- [ ] Check the tagged
      [GitHub Actions build](https://github.com/pylast/pylast/actions/workflows/deploy.yml)
      has deployed to [PyPI](https://pypi.org/project/pylast/#history)

- [ ] Check installation:

```bash
pip3 uninstall -y pylast && pip3 install -U pylast && python3 -c "import pylast; print(pylast.__version__)"
```
