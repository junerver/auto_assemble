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
# echo "start build uni-base"
# ./gradlew clean build
# echo "uni-base build done"
echo "--------------------------------"
echo "start cleanup app-distribution"
cd /app/distribution

# Initialize git lfs
echo "Initializing Git LFS..."
git lfs install

# Define branches to process
BRANCHES="master test release"

# Process each branch
for branch in $BRANCHES; do
    echo "--------------------------------"
    echo "Processing $branch branch..."
    
    # Switch to specified branch
    echo "Switching to $branch branch..."
    git checkout $branch
    
    # Force sync with remote branch
    echo "Force syncing $branch branch with remote..."
    git fetch origin
    git reset --hard "origin/$branch"
    git clean -fd
    
    # Pull LFS files
    echo "Pulling LFS files..."
    git lfs pull
    
    # Show current branch and recent commits
    echo "Current branch: $(git branch --show-current)"
    echo "Recent commits:"
    echo ""
    echo "$(git log -5 --pretty=format:"%n%h %s" | nl -w2 -s'. ')"
    echo ""
    
    echo "$branch branch sync completed"
done

# Perform repository cleanup
echo "--------------------------------"
echo "Starting repository cleanup..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive
echo "Repository cleanup completed"

echo "--------------------------------"
echo "app-distribution cleanup done"
echo "--------------------------------"
