# Project Plugins

`et-harness/main` 不保存任何真实项目的私有 Project Plugin、项目源码或项目知识库。

真实项目只存在于长期项目分支：

```text
project/<project-name>
```

每个项目分支由以下内容组成：

```text
当前 main 公共 Harness
+ 项目完整代码
+ 项目 Project Plugin
+ 项目 Knowledge / Rules / Architecture / Gates
```

`main` 只允许保留不依赖真实项目代码的 synthetic/example fixture。
