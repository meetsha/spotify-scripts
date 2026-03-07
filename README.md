# spotify-scripts
Scripts for spotify

## AWS Lambda Deploy

Use these commands from the repo root:

```bash
rm -rf package
rm -rf my-deployment-package.zip
mkdir package
pip3 install -r requirements.txt -t package/
cp newStashMaintainer.py .spotify_cache package/
cd package/
zip -r ../my-deployment-package.zip .
```

Then upload `my-deployment-package.zip` in the AWS Lambda web console.
