# monotop

Loose collection of scripts for the CMS Monotop analysis

# Software stack

Before executing any code in this repository, set up the software stack with the following command:

```bash
source setup.sh
```

## Yield tables

The script *monotop/scripts/yield_tables.py* is able to create yield tables based on output files of `Combine` fits. To create them, use the following command:

```
python monotop/scripts/yield_tables.py --combine-file <PATH TO COMBINE OUTPUT FILE> --output-path <PATH TO OUTPUT DIRECTORY>
```

Setting `--output-path` is optional, the default output location is the directory *store/yields*. The output is served as a directory with the base name of the combine file (without the *.root* extension). The compilation of LaTeX files to PDF files is also handled by the script, so you do not need to compile the files yourself. The output directory then consists of the following contents:

- a HDF file with a data frame containing the numerical values of yields and related uncertainties for all eras and regions,

- a PDF for each era and top tagger region (*pass* or *fail*) with the yield tables,

- a LaTeX source file, which the PDFs are generated from.
