# MeshRender Studio 使用指南

## 概述

MeshRender Studio 是一个本地浏览器工具，用于导入工程网格文件、生成适合 ParaView 的表面网格、定义可复用视角，并批量输出报告或审阅所需的渲染图片。

## 环境要求

- Python 3.9 或更高版本
- 已安装 ParaView，并可使用 `pvpython`
- 可访问本地网格输入文件

程序会按以下顺序查找 `pvpython`：`PVPYTHON`、`PATH`、`/Applications/ParaView-6.1.0.app/Contents/bin/pvpython`。

## 安装

1. 在项目目录打开终端。
2. 以可编辑模式安装：

```bash
python3 -m pip install -e .
```

## 启动应用

运行：

```bash
python3 -m meshrender_studio.app
```

然后在浏览器中打开 `http://127.0.0.1:5000`。

## 支持的输入类型

- Abaqus 输入文件：`.inp`
- AQWA 列表文件：`.LIS`
- ParaView 可直接读取的网格：`.vtu`
- 传统 VTK 网格：`.vtk`

导入后的文件会复制到当前项目的 `workspace/<project-id>/inputs/` 目录中，方便项目独立保存和重复运行。

## 项目目录结构

运行时主要使用以下本地目录：

- `projects/`：保存的项目 JSON
- `workspace/<project-id>/inputs/`：导入的源文件
- `workspace/<project-id>/mesh/`：生成的 VTU 网格
- `workspace/<project-id>/figures/`：生成的 PNG 图片

这些目录默认不应提交到 Git，以保持公开仓库整洁。

## 新建与加载项目

1. 点击 `New Project` 创建新项目模板。
2. 在 `Project Info` 中填写项目名称。
3. 点击 `Save Project` 保存当前配置。
4. 使用 `Saved projects` 下拉框和 `Load` 重新打开已有项目。

项目保存会保留数据源、视角、渲染默认值和输出目录设置。

## 导入和管理数据源

`Sources` 表格用于定义要预处理和渲染的对象。

- `Import Files` 会把一个或多个本地文件复制到项目工作区，并自动创建对应的数据源行。
- `Add Source Row` 可手动添加一行，用于已有相对路径文件。
- `Kind` 可以保持 `auto`，也可以手动指定类型。
- `Views` 支持填写一个或多个逗号分隔的视角名。
- `Figure Prefix` 用于控制输出文件名前缀。

对于 Abaqus 和 AQWA 工作流，仍可使用 `part_name`、`part_index` 和 `structure_filter` 进行更细的筛选。

## 编辑视角

`Views` 表格定义可被多个数据源复用的相机视角。

- `Azimuth`、`Elevation`、`Roll` 使用联动的滑块和数字输入框编辑。
- 这三个角度字段的单位都是 **度**。
- 滑块范围为 `-180` 到 `180`。
- `Zoom` 仍然使用数值因子。
- `Parallel` 用于控制该视角是否启用平行投影。

如果需要新增视角，点击 `Add View`，再在 `Sources` 表中引用该视角名称即可。

## 渲染默认参数

`Render Defaults` 区域用于控制共享渲染风格：

- 图像宽度和高度
- 背景色
- 表面颜色
- 边线颜色
- 线宽
- 表面透明度
- 默认平行投影设置

如果需要更细粒度的覆盖，也可以手动编辑保存后的 JSON。

## 渲染流程

1. 导入或定义至少一个数据源。
2. 确认项目视角与渲染默认值。
3. 点击 `Prepare + Render`。
4. 在 `Run Controls` 中查看状态和日志。
5. 任务完成后，在 `Results Gallery` 中查看输出图片。

对于 `.inp` 和 `.LIS` 输入，程序会先生成 VTU 网格，再调用 ParaView 渲染。对于 `.vtu` 和 `.vtk`，则直接使用现有网格进行渲染。

## 保存的项目与输出结果

保存的项目主要记录配置。生成的网格和图片保存在项目工作区中，需要时可以再次生成。

结果区域提供：

- PNG 预览图
- 生成网格文件的访问链接

## 故障排查

- 如果界面显示 ParaView 不可用，请确认 `pvpython` 已安装且可被找到。
- 如果数据源验证失败，请检查输入路径和文件扩展名是否正确。
- 如果任务完成但没有图片，请确认每个数据源至少关联了一个存在的视角名称。
- 如果导入文件较大，请仅将运行时输出保存在已忽略的 `projects/` 与 `workspace/` 中，不要提交到公开仓库。

## 作者

- Shuijin Li
- shuijinli@outlook.com
