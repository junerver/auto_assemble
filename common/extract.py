from pathlib import Path

import patoolib


def modern_extract(zip_path: Path, outdir: Path):
    """支持 Path 的解压封装"""
    patoolib.extract_archive(str(zip_path.resolve()), outdir=str(outdir.resolve()))
