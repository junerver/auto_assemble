echo "--------------------------------"
echo "start cleanup uni-base"
cd /app/uni-base
git reset --hard HEAD
git clean -fd
git pull
# 输出当前分支
echo "uni-base current branch: $(git branch --show-current)"
# 输出当前分支最近5次的commit message
echo "uni-base current commit:"
echo ""
echo "$(git log -5 --pretty=format:"%n%h %s" | nl -w2 -s'. ')"
echo ""
echo "uni-base cleanup done"
echo "--------------------------------"
echo "start build uni-base"
./gradlew clean build
echo "uni-base build done"
echo "--------------------------------"
echo "start cleanup app-distribution"
cd /app/distribution
git lfs install
git reset --hard HEAD
git clean -fd
git pull
# 输出当前分支
echo "app-distribution current branch: $(git branch --show-current)"
# 输出当前分支最近5次的commit message
echo "app-distribution current commit:"
echo ""
echo "$(git log -5 --pretty=format:"%n%h %s" | nl -w2 -s'. ')"
echo ""
echo "app-distribution cleanup done"
echo "--------------------------------"
