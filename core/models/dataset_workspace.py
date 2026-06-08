from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetWorkspace:

    root_directory: Path
    images_directory: Path
    labels_directory: Path
    previews_directory: Path
    info_file: Path

    @property
    def folder_name(self) -> str:
        return self.root_directory.name