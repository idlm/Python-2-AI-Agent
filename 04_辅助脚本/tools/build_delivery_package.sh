#!/usr/bin/env bash
set -euo pipefail

COURSE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DELIVERY_ROOT="${DELIVERY_ROOT:-${COURSE_ROOT%/*}/python_private_course_delivery}"
PACKAGE_ROOT="${DELIVERY_ROOT}/python_private_course_delivery"
ARCHIVE_PATH="${DELIVERY_ROOT}.zip"

rm -rf "${DELIVERY_ROOT}" "${ARCHIVE_PATH}"
mkdir -p \
  "${PACKAGE_ROOT}/01_教材章节" \
  "${PACKAGE_ROOT}/02_可运行项目" \
  "${PACKAGE_ROOT}/03_出版与审校记录" \
  "${PACKAGE_ROOT}/04_辅助脚本" \
  "${PACKAGE_ROOT}/05_教学测试" \
  "${PACKAGE_ROOT}/06_根目录配置"

copy_tree() {
  local source_rel="$1"
  local target_dir="$2"
  tar -C "${COURSE_ROOT}" \
    --exclude='*/.venv' \
    --exclude='*/__pycache__' \
    --exclude='*/.pytest_cache' \
    --exclude='*/.mypy_cache' \
    --exclude='*/.ruff_cache' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.egg-info' \
    --exclude='*.sqlite3' \
    --exclude='*.db' \
    --exclude='*.bak' \
    --exclude='*.log~' \
    -cf - "${source_rel}" | tar -C "${target_dir}" --strip-components=1 -xf -
}

copy_tree "01_教材章节/chapters" "${PACKAGE_ROOT}/01_教材章节"
copy_tree "02_可运行项目/projects" "${PACKAGE_ROOT}/02_可运行项目"
copy_tree "03_出版与审校记录/records" "${PACKAGE_ROOT}/03_出版与审校记录"
copy_tree "04_辅助脚本/tools" "${PACKAGE_ROOT}/04_辅助脚本"
copy_tree "05_教学测试/tests" "${PACKAGE_ROOT}/05_教学测试"
if [[ -d "${COURSE_ROOT}/examples" ]]; then
  copy_tree "examples" "${PACKAGE_ROOT}/examples"
fi

for root_file in README.md pyproject.toml .gitignore; do
  if [[ -f "${COURSE_ROOT}/${root_file}" ]]; then
    cp "${COURSE_ROOT}/${root_file}" "${PACKAGE_ROOT}/06_根目录配置/"
  fi
done

cat > "${PACKAGE_ROOT}/00_交付说明.md" <<'EOF'
# 《Python私房课》交付包

本交付包按用途分类，包含教材源文件、15 个可运行项目、出版与审校记录、辅助脚本、教学测试以及根目录配置。项目源代码保留 `pyproject.toml`、README、测试与 CI 定义；可在各项目目录中按 README 重新创建虚拟环境并执行质量门。

| 目录 | 内容 |
|---|---|
| `01_教材章节/chapters/` | 模块 0–15 的 Markdown 教材章节。 |
| `02_可运行项目/projects/` | 15 个项目的源代码、测试、README、配置与 CI 文件。 |
| `03_出版与审校记录/records/` | 课程目录、索引、ADR、Runbook、质量门禁、审计日志与状态记录。 |
| `04_辅助脚本/tools/` | 可复现的审计、修订和交付构建脚本。 |
| `05_教学测试/tests/` | 教材层测试。 |
| `06_根目录配置/` | 根 README、`pyproject.toml` 与 `.gitignore`（存在时）。 |

## 有意排除的本地文件

为保持压缩包轻量、可移植且不携带环境状态，已排除各项目 `.venv/`、缓存目录、`__pycache__/`、`.pyc`/`.pyo`、临时数据库/备份和构建元数据。课程不包含真实秘密、生产数据、部署工件或模型/网络调用凭据。

## 已记录的质量边界

出版记录中保留官方全书 312 项回归的既有证据、局部审校日志和已知的第三方弃用 warning。它们不构成真实模型质量、生产安全、部署、容量、成本、备份恢复或外部副作用授权。
EOF

(
  cd "${DELIVERY_ROOT}"
  zip -qr "${ARCHIVE_PATH}" "$(basename "${PACKAGE_ROOT}")" \
    -x '*/.venv/*' '*/__pycache__/*' '*/.pytest_cache/*' '*/.mypy_cache/*' '*/.ruff_cache/*' '*.pyc' '*.pyo'
)

sha256sum "${ARCHIVE_PATH}" > "${ARCHIVE_PATH}.sha256"
find "${PACKAGE_ROOT}" -type f | sort > "${DELIVERY_ROOT}/delivery_file_manifest.txt"
printf 'archive=%s\n' "${ARCHIVE_PATH}"
printf 'sha256=%s\n' "$(cut -d' ' -f1 "${ARCHIVE_PATH}.sha256")"
printf 'file_count=%s\n' "$(wc -l < "${DELIVERY_ROOT}/delivery_file_manifest.txt")"
