import argparse
import pandas as pd
import numpy as np
import zipfile
import logging

logger = logging.getLogger('converter')
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s | %(asctime)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")


def set_gnaf_loader_accuracy_codes():

    df = pd.DataFrame({'GEOCODE_TYPE_CODE': ['BC', 'PC', 'FCS', 'PCM', 'PAPS', 'STL', 'GG', 'LOC', 'PAP', 'UC', 'EAS', 'DF', 'BAP', 'FC', 'LB', 'EA'], 'accuracy': [
                      '1', '2', '2', '2', '3', '4', '4', '4', '5', '5', '5', '5', '5', '5', '5', '5']}, dtype='string')
    df.set_index('GEOCODE_TYPE_CODE', inplace=True)

    return df


def read_single_file(zip, zipfiles, name, pid):

    psv_path = next(zipfiles.rglob(name), None)
    if psv_path:
        logger.info(F'Reading from {psv_path}')
        with psv_path.open() as psv_file:
            df = pd.read_csv(psv_file, sep='|', index_col=pid,
                             low_memory=False, dtype='string')
    else:
        df = pd.DataFrame()
    return df


def read_state_files(zip, zipfiles, name_postfix, pid):

    states = ['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'OT']

    dfs = []
    for state in states:
        psv_path = next(zipfiles.rglob(state+name_postfix), None)
        if psv_path:
            logger.info(F'Reading from {psv_path}')
            with psv_path.open() as psv_file:
                dfs.append(pd.read_csv(psv_file, sep='|',
                                       index_col=pid, low_memory=False, dtype='string'))

    if dfs:
        merged = pd.concat(dfs)
    else:
        merged = pd.DataFrame()

    return merged


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('zipfile', help='G-NAF zip file')
    parser.add_argument('outfile', help='Name of the csv file to produce')
    parser.add_argument('-s', '--sort_id', action='store_true',
                        help='Sort the addresses by ADDRESS_DETAIL_PID')
    parser.add_argument('-d', '--drop_alias', action='store_true',
                        help='Only keep the principal addresses')
    parser.add_argument('-p', '--primary', action='store_true',
                        help='Drop the secondary addresses')
    parser.add_argument('-f', '--float', action='store_true',
                        help='Cast the lat/lon to a float so they can be written out with 8 decimal places')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Output progress information while running')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
        logger.info('Starting')

    with zipfile.ZipFile(args.zipfile, 'r') as zip:
        zipfiles = zipfile.Path(zip)
        logger.info(F'Reading from {args.zipfile}')
        addrs = read_state_files(
            zip, zipfiles, '_ADDRESS_DETAIL_psv.psv', 'ADDRESS_DETAIL_PID')
        streets = read_state_files(
            zip, zipfiles, '_STREET_LOCALITY_psv.psv', 'STREET_LOCALITY_PID')
        localities = read_state_files(
            zip, zipfiles, '_LOCALITY_psv.psv', 'LOCALITY_PID')
        states = read_state_files(zip, zipfiles, '_STATE_psv.psv', 'STATE_PID')
        geocodes = read_state_files(
            zip, zipfiles, '_ADDRESS_DEFAULT_GEOCODE_psv.psv', 'ADDRESS_DETAIL_PID')
        street_suffixs = read_single_file(
            zip, zipfiles, 'Authority_Code_STREET_SUFFIX_AUT_psv.psv', 'CODE')
        flat_types = read_single_file(
            zip, zipfiles, 'Authority_Code_FLAT_TYPE_AUT_psv.psv', 'CODE')

    logger.info('Building accuracy codes table')
    accuracy_codes = set_gnaf_loader_accuracy_codes()

    logger.info('Renaming columns and index')
    flat_types.rename(columns={'NAME': 'flat_type'}, inplace=True)
    geocodes.rename(columns={'LONGITUDE': 'lon',
                    'LATITUDE': 'lat'}, inplace=True)
    states.rename(columns={'STATE_ABBREVIATION': 'region'}, inplace=True)
    localities.rename(columns={'LOCALITY_NAME': 'city'}, inplace=True)
    addrs.rename(columns={'POSTCODE': 'postcode'}, inplace=True)
    addrs.rename_axis('id', inplace=True)
    if args.sort_id:
        logger.info('Sorting by ADDRESS_DETAIL_PID')
        addrs.sort_index(inplace=True)

#   Fill missing postcodes

    logger.info('Mapping LOCALITY_PID to postcodes')
    lookup_map = addrs.groupby('LOCALITY_PID')['postcode'].first()
    logger.info('Filling missing postcodes')
    addrs['postcode'] = addrs['postcode'].fillna(
        addrs['LOCALITY_PID'].map(lookup_map))

#   Removed extra spaces in street names
    logger.info('Building street names')
    streets['STREET_NAME'] = streets['STREET_NAME'].str.strip()
    streets['STREET_TYPE_CODE'] = streets['STREET_TYPE_CODE'].str.strip()
#   Fold in street suffixs
    streets = streets.join(
        street_suffixs['NAME'], on='STREET_SUFFIX_CODE', how='left')
#   Create full street name
    streets['street'] = streets['STREET_NAME'].str.cat(
        streets[['STREET_TYPE_CODE', 'NAME']], sep=' ', na_rep='').str.strip().str.replace('  ', ' ')

#   Fold in street names into addresses
    logger.info('Folding in street names to addresses')
    addrs = addrs.join(streets['street'], on='STREET_LOCALITY_PID', how='left')

#   Fold in state names with localities
    logger.info('Folding in state names to localities')
    localities = localities.join(states['region'], on='STATE_PID', how='left')

#   Fold localities into addresses
    logger.info('Folding in localities to addresses')
    addrs = addrs.join(localities[['city', 'region']],
                       on='LOCALITY_PID', how='left')

#   Fold flat types into addresses
    logger.info('Folding in flat types to addresses')
    addrs = addrs.join(flat_types['flat_type'],
                       on='FLAT_TYPE_CODE', how='left')

#   Fold in gnaf-loader style quality codes to geocodes
    logger.info('Folding in gnaf-loader style quality codes to geocodes')
    geocodes = geocodes.join(
        accuracy_codes['accuracy'], on='GEOCODE_TYPE_CODE', how='left')

    if args.float:
        logger.info('Casting lat and lon to floats')
        geocodes['lon'] = pd.to_numeric(geocodes['lon'], errors='coerce')
        geocodes['lat'] = pd.to_numeric(geocodes['lat'], errors='coerce')

#   Fold in geolocations
    logger.info('Folding in geolocations to addresses')
    addrs = addrs.join(geocodes[['lon', 'lat', 'accuracy']], how='left')

#   Build street numbers
    logger.info('Building street numbers')
#   Do them all as if they are not a range first
    addrs['number'] = addrs['NUMBER_FIRST_PREFIX'].fillna(
        '') + addrs['NUMBER_FIRST'].fillna('')+addrs['NUMBER_FIRST_SUFFIX'].fillna('')
#   Go back and add the end of the range if that exists
    addrs['number'] = np.where(addrs['NUMBER_LAST'].notnull(), addrs['number'].fillna('')
                               + '-'+addrs['NUMBER_LAST_PREFIX'].fillna('') + addrs['NUMBER_LAST']+addrs['NUMBER_LAST_SUFFIX'].fillna(''), addrs['number'])
#   Fill in the ones that have a lot number but no street number
    addrs['number'] = np.where(addrs['NUMBER_FIRST'].isnull() & addrs['LOT_NUMBER'].notnull(),
                               'LOT ' + addrs['LOT_NUMBER_PREFIX'].fillna('')+addrs['LOT_NUMBER']+addrs['LOT_NUMBER_SUFFIX'].fillna(''), addrs['number'])

#   Build the flat numbers
    logger.info('Building flat numbers')
    addrs['unit'] = np.where(addrs['flat_type'].notnull(), addrs['flat_type'].fillna('')
                             + ' '+addrs['FLAT_NUMBER_PREFIX'].fillna('')+addrs['FLAT_NUMBER'].fillna('')+addrs['FLAT_NUMBER_SUFFIX'].fillna(''), None)

#   Drop addresses that have no confidence
    logger.info('Dropping the addresses that have no confidence')
    logger.info(F'Number of addresses before: {len(addrs.index):,d}')
    addrs = addrs[addrs['CONFIDENCE'] != '-1']
    logger.info(F'Number of addresses after: {len(addrs.index):,d}')

    if args.drop_alias:
        logger.info('Dropping the addresses that are aliases')
        logger.info(F'Number of addresses before: {len(addrs.index):,d}')
        addrs = addrs[addrs['ALIAS_PRINCIPAL'] == 'P']
        logger.info(F'Number of addresses after: {len(addrs.index):,d}')

    if args.primary:
        logger.info('Dropping the addresses that are secondary')
        logger.info(F'Number of addresses before: {len(addrs.index):,d}')
        addrs = addrs[addrs['PRIMARY_SECONDARY'].fillna('P') == 'P']
        logger.info(F'Number of addresses after: {len(addrs.index)}:,d')

    logger.info(F'Writing results to: {args.outfile}')
    addrs[['number', 'street', 'unit', 'lon', 'lat', 'city', 'postcode',
           'region', 'accuracy']].to_csv(args.outfile, float_format='%.8f')

    logger.info('Finished')
