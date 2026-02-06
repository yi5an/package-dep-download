import os
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional


class PackageDownloader:
    """多线程包下载器"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.session = requests.Session()

    def download_packages(
        self,
        packages: List[Dict],
        output_dir: Path,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """批量下载包"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {"success": [], "failed": [], "total": len(packages)}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_single, pkg, output_dir): pkg
                for pkg in packages
            }

            for i, future in enumerate(as_completed(futures), 1):
                pkg = futures[future]
                try:
                    filepath = future.result()
                    results["success"].append(filepath)

                    if progress_callback:
                        progress_callback(i, len(packages), pkg)

                except Exception as e:
                    results["failed"].append({"package": pkg, "error": str(e)})

        return results

    def _download_single(self, pkg: Dict, output_dir: Path) -> Path:
        """下载单个包"""
        url = pkg.get("url")
        if not url:
            raise ValueError(f"Package {pkg.get('name')} has no URL")

        filename = os.path.basename(url)
        filepath = output_dir / filename

        response = self.session.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath
