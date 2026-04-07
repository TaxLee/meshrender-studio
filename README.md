# MeshRender Studio

## English

MeshRender Studio is a local Flask application for preparing engineering mesh data and generating consistent comparison figures for different meshes under the same viewing angle and render settings.

![MeshRender Studio example 1](docs/assets/Mesh1.png)
![MeshRender Studio example 2](docs/assets/Mesh2.png)

### Features

- Import Abaqus `.inp`, AQWA `.LIS`, `.vtu`, and `.vtk` sources.
- Generate directly comparable figures for different meshes using shared camera views.
- Edit shared render settings and manage reusable source/view presets.
- Adjust `azimuth`, `elevation`, and `roll` with degree-based sliders.
- Queue mesh preparation and ParaView rendering from the browser.
- Save projects locally and review generated figures and mesh outputs.

### Install

```bash
python3 -m pip install -e .
```

ParaView `pvpython` must be available from `PVPYTHON`, `PATH`, or `/Applications/ParaView-6.1.0.app/Contents/bin/pvpython`.

### Run

```bash
python3 -m meshrender_studio.app
```

Open `http://127.0.0.1:5000`.

### Project Layout

- `meshrender_studio/`: application package, Flask UI, and rendering logic.
- `projects/`: saved project JSON files created locally at runtime.
- `workspace/<project-id>/inputs/`: imported source files.
- `workspace/<project-id>/mesh/`: generated VTU meshes.
- `workspace/<project-id>/figures/`: rendered PNG figures.

### Guides

- English: [docs/user-guide.en.md](docs/user-guide.en.md)
- Chinese: [docs/user-guide.zh-CN.md](docs/user-guide.zh-CN.md)

### Author

- Shuijin Li
- shuijinli@outlook.com

### License

MIT. See [LICENSE](LICENSE).

## 中文

MeshRender Studio 是一个本地 Flask 工具，用于整理工程网格数据，并在相同观察视角与相同渲染参数下，为不同网格生成可直接对比的图片，无需手动修改 JSON。

![MeshRender Studio 示例 1](docs/assets/Mesh1.png)
![MeshRender Studio 示例 2](docs/assets/Mesh2.png)

### 功能

- 支持导入 Abaqus `.inp`、AQWA `.LIS`、`.vtu`、`.vtk`。
- 支持在统一观察视角下为不同网格生成可对比图片。
- 支持统一渲染参数、可复用视角与数据源配置。
- 支持用角度滑块调整 `azimuth`、`elevation`、`roll`。
- 可在浏览器内执行网格预处理与 ParaView 渲染。
- 支持本地保存项目，并查看生成的图片和网格文件。

### 安装

```bash
python3 -m pip install -e .
```

需要保证 ParaView `pvpython` 可通过 `PVPYTHON`、`PATH` 或 `/Applications/ParaView-6.1.0.app/Contents/bin/pvpython` 访问。

### 运行

```bash
python3 -m meshrender_studio.app
```

打开 `http://127.0.0.1:5000`。

### 项目目录

- `meshrender_studio/`：应用包、Flask 界面与渲染逻辑。
- `projects/`：运行时本地保存的项目 JSON。
- `workspace/<project-id>/inputs/`：导入的源文件。
- `workspace/<project-id>/mesh/`：生成的 VTU 网格。
- `workspace/<project-id>/figures/`：生成的 PNG 图片。

### 文档

- English: [docs/user-guide.en.md](docs/user-guide.en.md)
- 中文: [docs/user-guide.zh-CN.md](docs/user-guide.zh-CN.md)

### 作者

- Shuijin Li
- shuijinli@outlook.com

### 许可

MIT。详见 [LICENSE](LICENSE)。
