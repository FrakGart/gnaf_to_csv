# gnaf_to_csv
A Python script to convert Geoscape's open GNAF files into a single CSV file.

```
 usage: gnaf_to_csv.py [-h] [-s] [-d] [-p] [-f] [-v] zipfile outfile`

positional arguments:
  zipfile           G-NAF zip file
  outfile           Name of the csv file to produce

options:
  -h, --help        show this help message and exit
  -s, --sort_id     Sort the addresses by ADDRESS_DETAIL_PID
  -d, --drop_alias  Only keep the principal addresses
  -p, --primary     Drop the secondary addresses
  -f, --float       Cast the lat/lon to a float so they can be written out with 8 decimal places
  -v, --verbose     Output progress information while running
```

Inspired by [gnaf.sh](https://github.com/openaddresses/openaddresses/blob/master/scripts/au/gnaf.sh) from the [openaddresses](https://github.com/openaddresses/openaddresses) project, which itself uses minus34's [gnaf-loader](https://github.com/minus34/gnaf-loader).

I wanted something that would be less fussy to use and also able to drop alias addresses.

This script doesn't quite produce the same results as gnaf.sh, out of the 15,794,643 addresses there are 1,262 differences. [diffs_2025-08.csv](diffs_2025-08.csv) is the result of a [`qsv diff`](https://github.com/dathere/qsv). The gnaf.sh version has a number of missing postcodes and contains a number of odd looking number ranges containing no last number only a suffix eg 130B-B. There is a difference of opinion of where the split between the 3000 and 3004 postcodes is. The rest of the differences seem to be in the assigning to locality.

