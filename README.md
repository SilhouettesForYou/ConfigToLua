### Convert to `.lua`

1. 执行`pip install -r requirements.txt`
2. 配置 `.config`文件

   1. 第一行设置`.csv`文件路径，以`#`分割 e.g. `csv#E:\WorkSpace\ROGame-1.5\config\Table`
   2. 设置文件名，以`;`分割 e.g. `SkillTable;SkillEffectUuidTable`
   3. 第三行设置`SkillData`文件路径，以`#`分割 e.g. `xml#E:\WorkSpace\ROGame-dev\config\Assets\Resources\SkillData`

3. 生成`lua`脚本

    ```shell
    python main.py --xml # 将SkillData中的.txt文件转成.lua文件
    python main.py --for [server|client] --csv # 将Table中的.csv文件转成.lua文件 --for用于指定生成客户端还是服务器l代码
    python main.py --all # 相当于执行上述两步操作
    ```