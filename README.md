# Differential 差速器
一个可以自动生成PTGen，MediaInfo，截图，并且生成发种所需内容的脚本


# 为什么叫差速器
差速器是汽车上的一种能使左、右轮胎以不同转速转动的结构。使用同样的动力输入，差速器能够输出不同的转速。就如同这个工具之于PT资源，差速器帮你使用同一份资源，输出不同PT站点需要的发种数据。

# 差速器能做什么？
当把大部分配置填好时，你可以仅提供资源文件的路径和一个豆瓣链接，差速器会帮你生成发种所需要的影片信息，Mediainfo，截图并上传图床，nfo文件，种子文件，并自动填写发种页面的表单（ 感谢树大的[脚本](https://github.com/techmovie/easy-upload) ）

![](./usage.gif)

# 如何安装差速器

## Linux

```shell
# 安装ffmpeg和mediainfo
sudo apt install ffmpeg mediainfo
pip3 install Differential
```

## Windows

安装下载并安装Python和ffmpeg，然后把ffmpeg放到Path或者你的工作目录，确认在你的工作目录`ffmpeg.exe -version`有正确输出。

```PowerShell
pip.exe install Differential
```

## Mac OS

```shell
# 安装ffmpeg
brew install ffmpeg
pip install Differential
```

# 如何使用差速器

差速器支持未经过重大修改的NexusPHP站点以及部分支持[easy-upload](https://github.com/techmovie/easy-upload)支持的站点。
在使用前，请先使用`dft -h`查看本工具支持的站点/现有的插件。

请先参考`config.ini.example`，在`Default`块填上各个站点/插件通用的参数，比如图床相关的几个参数，然后在各站点/插件名字对应的块填上各自特有的参数，比如截图张数等等。

当配置文件完成后，你可以通过以下命令，一键获取发种所需要的信息。当然你也可以选择通过命令行来传递所有参数。
```shell
dft [插件名字] -f [种子文件夹] -u [豆瓣URL]
```

主要参数介绍：
 
- `config`: 配置文件的位置，默认读取当前文件夹下的`config.ini`
- `log`: log文件的路径
- `folder`: 种子文件或文件夹的路径
- `url`: 影片的豆瓣链接，事实上，所有PTGen支持的链接这里都支持
- `make_torrent`: 是否制种，默认关闭
- `geenrate_nfo`: 是否利用mediainfo生成nfo文件，默认关闭
- `screenshot_count`: 截图生成的张数，默认为0，即不生成截图
- `image_hosting`: 图床的名称，现在支持ptpimg,chevereto,imgurl和SM.MS
- `image_hosting_url`: 如果是自建的图床，提供图床链接
- `ptgen_url`: PTGen的地址，默认是我自建的PTGen，可能会不稳定
- `announce_url`: 制种时的announce地址

## NexusPHP

相比基础参数，`NexusPHP`插件特有的参数有：

- `upload_url`: 发种页面的地址
- `encoder_log`: 压制log的地址，如果提供的话会在介绍的mediainfo部分附上压制log
- `easy_upload`: 默认开启，关闭的话会直接在命令行输出主/副标题，描述和mediainfo
- `trim_description`: 默认关闭，开启的话会省略掉上传链接的描述部分，以避免链接过长浏览器无法打开的问题

## 其他插件

为保护站点信息，请到[`plugins`](https://github.com/LeiShi1313/Differential/tree/main/differential/plugins)文件夹查看或者`dft [插件名称] -h`查看支持的参数


# TODO
- [] 更好的出错管理
- [x] 识别已经生成过的截图，不重复截图