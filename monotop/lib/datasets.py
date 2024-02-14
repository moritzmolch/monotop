import glob
import os
import re
from typing import List, Optional
import yaml


class Dataset():

    dump_keys = {
        "name",
        "key",
        "filelist",
        "cross_section",
        "is_data",
        "is_mc",
    }

    def __init__(
        self,
        name: str,
        key: Optional[str] = None,
        filelist: Optional[List[str]] = None,
        cross_section: Optional[float] = None,
        is_data: Optional[bool] = None,
        is_mc: Optional[bool] = None,
    ):
       self._name = name
       self._key = key or ""
       self._filelist = filelist or []
       self._cross_section = cross_section or 1.0
       
       self._is_data = is_data if is_data is not None else False
       self._is_mc = is_mc if is_mc is not None else False

    @property
    def name(self):
        return self._name

    @property
    def filelist(self):
        return list(self._filelist or [])

    @property
    def key(self):
        return self._key

    @property
    def cross_section(self):
        return self._cross_section

    @property
    def is_data(self):
        return self._is_data

    @property
    def is_mc(self):
        return self._is_mc

    def dump(self, file_path: os.PathLike):
        with open(file_path, mode="w") as f:
            yaml.safe_dump({k: getattr(self, k) for k in self.dump_keys}, f)

    def compile_filelist(self):

        # divide the DAS key into its parts
        key_parts = self.key.split("/")

        # if no valid key is given, filelist cannot be compiled
        if len(key_parts) < 2:
            raise RuntimeError("dataset '{}' does not have a DAS key".format(self.name))

        # get the dataset name (full part between the first two slashes)
        dataset_name = key_parts[1]

        # evaluate the part between the second and the third slash, which gives the production tag and the user
        m = re.match("^((\w+)-KITv2_CustomNanoV9_((MC)|(Data))_([\w\d]+))-([\w\d]+)$", key_parts[2])
        if m is not None:
            raise RuntimeError("DAS key of dataset '{}' does not follow expected pattern".format(self.name))
        production_tag = m.group(1)
        user = m.group(2)

        # from here on, let glob do the rest of the work
        filelist = list(
            glob.glob(
                os.path.join(
                    "/pnfs/desy.de/cms/tier2/store/user",
                    user,
                    "customNano",
                    dataset_name,
                    production_tag,
                    "**",
                )
            )
        )

        self._filelist = filelist

        return filelist


class DatasetGroup():

    def __init__(
        self,
        name: str,
        datasets: Optional[List[Dataset]] = None,
    ):
        self._name = name
        self._datasets = datasets or None

    @property
    def name(self):
        return self._name
    
    @property
    def datasets(self):
        return list(self._datasets)

    def add_dataset(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], Dataset):
            dataset = args.pop(0)
            self._add_dataset_object(dataset)
        else:
            self._add_dataset_object(Dataset(*args, **kwargs))

    def _add_dataset_object(self, dataset: Dataset):
        if dataset.name in [dataset.name for dataset in self._datasets]:
            raise ValueError(
                "dataset with name '{}' already exists in dataset group '{}'".format(
                    dataset.name,
                    self.name,
                )
            )

    def dump(self, directory_path: os.PathLike):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            for dataset in self.datasets:
                dataset.dump(os.path.join(directory_path, dataset.name))
