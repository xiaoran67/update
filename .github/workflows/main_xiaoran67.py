name: 'Update schedule xiaoran67'

on:
  schedule:
    - cron: '0 22,10 * * *'
  workflow_dispatch:
    inputs:
      branch:
        description: '要运行的分支（留空则自动选择）'
        required: false
        default: ''
        type: string

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - name: Determine target branch
        id: vars
        run: |
          # 手动触发且有输入分支时，使用输入的分支
          if [ "${{ github.event_name }}" = "workflow_dispatch" ] && [ -n "${{ github.event.inputs.branch }}" ]; then
            TARGET_BRANCH="${{ github.event.inputs.branch }}"
            echo "🎯 使用手动指定的分支: $TARGET_BRANCH"
          else
            # 自动选择：根据仓库所有者
            if [ "${{ github.repository_owner }}" = "xiaoran67" ]; then
              TARGET_BRANCH="main"
              echo "🤖 自动选择: xiaoran67仓库 -> main分支"
            else
              TARGET_BRANCH="master"
              echo "🤖 自动选择: 其他仓库 -> master分支"
            fi
          fi
          
          echo "BRANCH_NAME=$TARGET_BRANCH" >> $GITHUB_ENV
          echo "📁 仓库所有者: ${{ github.repository_owner }}"
          echo "🚀 触发事件: ${{ github.event_name }}"
          echo "✅ 最终分支: $TARGET_BRANCH"
          
      - uses: actions/checkout@v3
        with:
          ref: ${{ env.BRANCH_NAME }}
          
      - name: Run with setup-python 3.13
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
          update-environment: true
          cache: 'pipenv'
          
      - name: Check open_driver config
        id: check_driver
        run: |
          echo "OPEN_DRIVER=$(python -c '
          try:
            from utils.config import config
            open_driver = config.open_driver
          except:
            open_driver = False
          print(open_driver)')" >> $GITHUB_ENV
          echo "🔧 OPEN_DRIVER配置: ${{ env.OPEN_DRIVER }}"
          
      - name: Set up Chrome
        if: env.OPEN_DRIVER == 'True'
        uses: browser-actions/setup-chrome@latest
        with:
          chrome-version: stable
          
      - name: Download chrome driver
        if: env.OPEN_DRIVER == 'True'
        uses: nanasess/setup-chromedriver@master
        
      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg
        
      - name: Install pipenv
        run: pip3 install --user pipenv
        
      - name: Install dependencies
        run: pipenv --python 3.13 && pipenv install --deploy
        
      - name: Install selenium
        if: env.OPEN_DRIVER == 'True'
        run: pipenv install selenium
        
      - name: Update
        run: pipenv run dev
        
      - name: Commit and push if changed
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add .
          if ! git diff --staged --quiet; then
            git commit -m "Github Action Auto Updated"
            git push --force
          fi