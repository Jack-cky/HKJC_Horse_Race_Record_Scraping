"""
UTILITIES
Version 04
    This programme provides functions to avoid reduplicated scripting.
Contribution: Jack Chan
"""

import os
import time
import pandas as pd
from tabulate import tabulate

def print_msg(msg, p_type = 'fancy_grid'):
    print(tabulate([[msg]], tablefmt = p_type))
    
    return None

def elapse_time(function):
    def wrapper(*args, **args_keys):
        time_lapse = time.time()
        result = function(*args, **args_keys)
        min, sec = tuple(map(int, divmod(time.time() - time_lapse, 60)))
        print_msg(f'Above task took {min} minute(s) {sec} second(s) for execution.')
        
        return result
    return wrapper

def restore_df(file_name, print_action = False):
    if os.path.exists(f'./cache/{file_name}.parquet'):
        print_msg(f'Restoring cache file ({file_name})...') if print_action else None
        df = pd.read_parquet(f'./cache/{file_name}.parquet')
    else:
        print_msg(f'Creating cache file ({file_name})...') if print_action else None
        df = pd.DataFrame()
    
    return df

def cache_df(file_name, tab_idx, print_summary = True):
    def inner_decorator(function):
        def wrapper(*args, **args_keys):
            df_merge = function(*args, **args_keys)
            
            if df_merge is None:
                return df_merge
            
            pk = [tab_idx, [tab_idx]][isinstance(tab_idx, str)]
            
            if any([idx not in df_merge.columns for idx in pk]):
                return df_merge
            
            if not os.path.exists('./cache'):
                os.makedirs('./cache')
            
            df = restore_df(file_name)
            
            if df.shape[0] == 0:
                df_merge.to_parquet(f'./cache/{file_name}.parquet')
                print_msg(f'{df_merge.shape[0]} record(s) cached onto local file.') if print_summary else None
            
            if all([idx in df.columns for idx in pk]):
                df['_'.join(pk)] = df[pk].sum(axis = 1)
                df_merge['_'.join(pk)] = df_merge[pk].sum(axis = 1)
                idx = [idx for idx in df_merge['_'.join(pk)].unique() if idx not in df['_'.join(pk)].unique()]
                df = pd.concat([df, df_merge.query(f"{'_'.join(pk)} in @idx")], ignore_index = True)
                
                if isinstance(tab_idx, list):
                    df.drop(columns = ['_'.join(pk)], inplace = True)
                    df_merge.drop(columns = ['_'.join(pk)], inplace = True)
                
                if len(idx) != 0:
                    df.to_parquet(f'./cache/{file_name}.parquet')
                    print_msg(f'{len(idx)} record(s) appended onto local file.') if print_summary else None
            
            return df_merge
        return wrapper
    return inner_decorator