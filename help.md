#### 参数说明

##### 由`.csv`文件生成`.lua`文件

* `-f/--for`：有参数选项，**默认值为`client`**
  * 生成服务器`.lua`文件 e.g. `-f server`
  * 生成客户端`.lua`文件 e.g. `-f client`
* `-k/--key`：无参数选项；是否生成字段的key
* `-i/--index`：无参数选项；是否生成字段的索引，与key互斥
* `-s/--string`：有参数选项，无默认值；提取所有字符串并保存至`.lua`文件中
  * `only`表示仅写入字符串文件，不写入由`.csv`文件生成`.lua`文件
  * `all`表示既写入字符串文件，又写入由`.csv`文件生成`.lua`文件
* `--require`：有参数选项，无默认值；生成服务器`init.lua`用于加载所有lua脚本
  * `only`表示仅保存`init.lua`文件，不写入由`.csv`文件生成`.lua`文件
  * `all`表示既保存`init.lua`文件，又写入由`.csv`文件生成`.lua`文件
* `-c/-csv`：由`.csv`文件生成`.lua`文件标识，必须放置命令行末尾

```shell
python main.py -f client -i -s all -c
```

##### 由`xml`文件生成`.lua`文件

* `-x/-xml`：由`xml`文件生成`.lua`文件标识

```shell
python main.py --xml
```

##### 由`.pkg`文件生成`.cpp`文件

* `-p/-pkg`：由`.pkg`文件生成`.cpp`文件标识

```shell
python main.py --pkg
```