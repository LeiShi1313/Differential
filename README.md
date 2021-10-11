# Differential 差速器
一个可以自动生成PTGen，MediaInfo，截图，并且生成发种所需内容的脚本


# 为什么叫差速器
差速器是汽车上的一种能使左、右轮胎以不同转速转动的结构。使用同样的动力输入，差速器能够输出不同的转速。就如同这个工具之于PT资源，差速器帮你使用同一份资源，输出不同PT站点需要的发种数据。

# 它能做什么？
当把大部分配置填好时，你可以仅提供资源文件的路径和一个豆瓣链接，差速器会帮你生成发种所需要的影片信息，Mediainfo，截图并上传图床，nfo文件，种子文件，并自动填写发种页面的表单（ 感谢树大的[脚本](https://github.com/techmovie/easy-upload) ）效果如图
![](./usage.gif)

# 如何使用

差速器现在支持未经过重大修改的NexusPHP站点。在使用前，请先使用`python differential/main.py -h`查看本工具现有的插件。如果你需要的站点没有支持，可以尝试`NexusPHP`插件并手动指定发种页面，其他的参数还请参考`python differential/main.py nexusphp -h`和`config.ini.example`。

TODO


# TODO
- [] 更好的出错管理
- [] 识别已经生成过的截图，不重复截图