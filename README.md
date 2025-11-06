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

