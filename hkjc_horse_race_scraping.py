"""
HONG KONG JOCKEY CLUB HORSE RACE DATA SCRAPER
Version 08
    This programme scraps horse race result from HKJC just for fun.
        A. Historical Horse Race Record
            f(.) = query_horse_race_result(race_date, race_no, is_addit_info)
                1.  Input a STR race date, an INT race number and a BOOL flag for additonal info.
                2.  Output race result, horse info, trainer info and jockey info as a data frame.
        B. Current Odds Menu Table
            g(.) = query_odds_menu(race_no, is_addit_info)
                1.  Input an INT race number and a BOOL flag for additonal info.
                2.  Output current odds table on given race number.
Contribution: Jack Chan
"""

import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import utilities

class HongKongJockeyClubHorseRace():
    def __init__(self) -> None:
        # HKJC URLs related result, trainer, jockey and horse
        self.__url = 'https://racing.hkjc.com/racing/information/English'
        self.__url_result = f'{self.__url}/Racing/LocalResults.aspx'
        self.__url_trainer = f'{self.__url}/Trainers/TrainerProfile.aspx'
        self.__url_jockey = f'{self.__url}/Jockey/JockeyProfile.aspx'
        self.__url_horse = f'{self.__url}/Horse/Horse.aspx'
        self.url_odds = 'https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=en'
        
        # HTML tags
        self.__tag_date = "//span[@class='f_fr']"
        self.__tag_card = "//table[@class='f_fs12 f_fr js_racecard']/tbody/tr/td"
        self.__tag_venue = "//span[contains(@class,'f_fl f_fs13')]"
        self.__tag_race_tag = "//div[contains(@class,'race_tab')]"
        self.__tag_performance = "//div[@class='performance']"
        self.__tag_trainer = "//div[@class='trainer_right f_fs11']"
        self.__tag_jockey = "//div[@class='jockey_right bg_ee']"
        self.__tag_season_tab = "//div[contains(@class,'seasonTab')]"
        self.__tag_horse = "//table[@class='horseProfile']"
        self.__odds_date_venue = "//div[@class='mtgInfoLeft']"
        self.__odds_race_tag = "//div[@style='padding:3px 3px 3px 3px']/div"
        self.__odds_id = "//div[@id='winplaceTable']/table/tbody"
        self.__odds_menu = "//div[@id='winplaceTable']"
    
    def __get_default_settings(self, web) -> None:
        web.get(self.__url_result)
        WebDriverWait(web, 10).until(
            EC.presence_of_element_located((By.XPATH, self.__tag_date))
        )
        
        self.__race_date = pd.to_datetime(
            re.findall(r'(\d{2,4}/\d{2,4}/\d{2,4})(?=</option>)', web.page_source)
            , format = '%d/%m/%Y'
        ).strftime('%Y/%m/%d')
        
        self.__race_date = self.__race_date[
            self.__race_date < datetime.today().strftime('%Y/%m/%d')
        ]
        
        df = utilities.restore_df('hkjc_horse_race')
        if 'race_date' in df.columns:
            self.__race_date = self.__race_date[self.__race_date > df['race_date'].max()]
        
        del df
        return None
    
    @utilities.elapse_time
    @utilities.cache_df('hkjc_race_result', ['race_date', 'index'])
    def __get_race_result(self, web, race_date, race_no) -> pd.DataFrame:
        
        def restore_race_result() -> pd.DataFrame:
            df = utilities.restore_df('hkjc_race_result')
            
            # restore by race date
            if 'race_date' in df.columns:
                df = df.query(f'race_date == "{race_date}"')[[
                    'race_date', 'race_venue', 'sec_div_no', 'index', 'race_class'
                    , 'distance', 'rating_range', 'going', 'race_name', 'track', 'course'
                    , 'pool', 'time', 'sectional_time', 'horse_id', 'jockey_id', 'trainer_id'
                    , 'place', 'horse_no', 'horse', 'jockey', 'trainer', 'actual_weight'
                    , 'on_date_weight', 'draw', 'length_behind_winner', 'running_position'
                    , 'finish_time', 'win_odds'
                ]]
                # restore by race number
                if df.query(f'sec_div_no == "{race_no}"').shape[0] != 0:
                    df = df.query(f'sec_div_no == "{race_no}"')
            
            return df
        
        def is_invalid_data(web, race_date, race_no) -> bool:
            # bypass invalid race date input
            if (race_date is not None) & (race_date not in self.__race_date):
                utilities.print_msg(f'Race date {race_date} was not hosting horse race!', 'simple')
                return True
            
            # keep only local horse race
            if 'overseas' in web.current_url:
                utilities.print_msg(f'Date {race_date} was an oversea race!', 'simple')
                return True
            
            # prevent abandoned race record
            if 'refund' in web.page_source:
                utilities.print_msg(f'Date {race_date} was an abandoned race!', 'simple')
                return True
            
            # avoid input race_no out of bound
            if race_no is not None:
                n_race = web.find_elements_by_xpath(self.__tag_card)
                if race_no not in range(1, len(n_race) - 1):
                    utilities.print_msg(f'Race No. {race_no} did not exist on date {race_date}!', 'simple')
                    return True
            
            return False
        
        def get_race_card_index(card) -> int:
            cnt = 0
            for val in card:
                if 'ResultsAll' in val.get_attribute("innerHTML"):
                    break
                elif 'img' in val.get_attribute("innerHTML"):
                    cnt += 1
            
            return cnt
                
        def get_race_info(race_date, race_venue, race_tab) -> pd.DataFrame:
            rt = race_tab.split('\n')
            
            df = pd.DataFrame({
                'race_date': race_date
                , 'race_venue': race_venue
                , 'sec_div_no': re.findall(r'RACE (\d{1,2})', rt[0])
                , 'index': re.findall(r'\((\d{1,3})\)', rt[0])
                , 'race_class': re.findall(r'(.*) - \d+M', rt[1])
                , 'distance': re.findall(r'(\d{1,4})M', rt[1])
                , 'rating_range': re.findall(r'\((.*)\)', ['(NA)', rt[1]]['(' in rt[1]])
                , 'going': re.findall(r'Going : (.*)', rt[1])
                , 'race_name': re.findall(r'(.*) Course :', rt[2])
                , 'track': ['ALL WEATHER TRACK', 'TURF']['TURF' in rt[2]]
                , 'course': re.findall(r'\"(.*)\"', ['"AWT"', rt[2]]['TURF' in rt[2]])
                , 'pool': re.findall(r'HK\$ ([0-9,]+)', rt[3])
                , 'time': re.findall(r'\(.*\)', rt[3])
                , 'sectional_time': re.findall(r': ([0-9\s.:]+)', rt[4])
            })
            
            return df
        
        def get_instance_id(html) -> pd.DataFrame:
            df = pd.DataFrame.from_dict({
                'horse_id': re.findall(r'(?<=HorseId=)(.*)\"\s?(?=class)', html)
                , 'jockey_id': re.findall(r'(?<=JockeyId=)(.*)(?=&amp;)', html)
                , 'trainer_id': re.findall(r'(?<=TrainerId=)(.*)(?=&amp;)', html)
            }, orient = 'index').T.fillna('---')
            
            return df
        
        df = restore_race_result()
        
        if df.shape[0] != 0:
            return df
        
        web.get(f'{self.__url_result}?RaceDate={race_date}')
        
        # handle unexpected results
        if is_invalid_data(web, race_date, race_no):
            return None
        
        # get racing venue
        race_venue = web.find_element_by_xpath(self.__tag_venue).text
        race_venue = ['HV', 'ST']['Sha Tin' in race_venue]
        
        # reload web browser with full URL
        web.get(f'{self.__url_result}?RaceDate={race_date}&Racecourse={race_venue}')
        WebDriverWait(web, 20).until(
            EC.presence_of_element_located((By.XPATH, self.__tag_card))
        )
        
        race_card = get_race_card_index(web.find_elements_by_xpath(self.__tag_card))
        
        for race_idx in range(1, race_card + 1):
            # allocate target race number if defined
            if (race_no is not None) & (race_no != race_idx):
                continue
            
            # reload web browser with full URL
            web.get(f'{self.__url_result}?RaceDate={race_date}&Racecourse={race_venue}&RaceNo={race_idx}')
            try:
                WebDriverWait(web, 20).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_race_tag))
                )
            except:
                # stop when data is not yet available
                utilities.print_msg(f'Race card {race_idx} is not yet available', 'simple')
                break
            
            # get race details
            race_info = get_race_info(
                race_date, race_venue, web.find_element_by_xpath(self.__tag_race_tag).text
            )
            
            # get individuals id
            instance_id = get_instance_id(web.page_source)
            
            # get horse race result
            race_result = pd.read_html(
                web.find_element_by_xpath(self.__tag_performance).get_attribute('outerHTML')
            )[0].set_axis(
                ['place', 'horse_no', 'horse', 'jockey', 'trainer'
                , 'actual_weight', 'on_date_weight', 'draw'
                , 'length_behind_winner', 'running_position', 'finish_time', 'win_odds']
                , axis = 1
            )
            
            # quick remediation on data type
            race_result[['place', 'on_date_weight', 'draw', 'win_odds']] = \
                race_result[['place', 'on_date_weight', 'draw', 'win_odds']].astype(str)
            
            # combine information
            df_merge = pd.concat([race_info, instance_id], axis = 1).fillna(method = 'ffill')
            df_merge = pd.concat([df_merge, race_result], axis = 1)
            df = pd.concat([df, df_merge], ignore_index = True)
            del race_info, instance_id, race_result, df_merge
            
            utilities.print_msg(f'Done for {race_idx} race card!', 'simple') if race_no is None else None
        
        return df
    
    @utilities.elapse_time
    @utilities.cache_df('hkjc_trainer_info', 'trainer_id')
    def get_trainer_info(self, web, trainer_id) -> pd.DataFrame:
        
        def restore_trainer_info(ids):
            df = utilities.restore_df('hkjc_trainer_info')
            
            ids = ids[ids != '---']
            
            if 'trainer_id' in df.columns:
                ids_original = ids.copy()
                ids = [val for val in ids if val not in df['trainer_id'].unique()]
                df = df.query('trainer_id in @ids_original')
            utilities.print_msg(f'Pending {len(set(ids))} trainer id(s)...', 'orgtbl') if len(ids) else None
            
            return df, ids
        
        df, trainer_id = restore_trainer_info(trainer_id)
        
        for id in set(trainer_id):
            try:
                web.get(f'{self.__url_trainer}?TrainerId={id}')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_trainer))
                )
            except:
                web.get(f'{self.__url_trainer}?TrainerId={id}&Season=Previous')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_trainer))
                )
            
            content = pd.read_html(
                web.find_element_by_xpath(self.__tag_trainer).get_attribute('outerHTML')
            )[0][0]
            
            df_merge = pd.DataFrame({
                'trainer_id': [id]
                , 'trainer_name': [content[0]]
                , 'trainer_age': re.findall(r'\d{1,3}', content[1])
                , 'trainer_last_update': datetime.today().strftime('%Y')
            })
            
            df = pd.concat([df, df_merge], ignore_index = True)
            del content, df_merge
        
        return df
    
    @utilities.elapse_time
    @utilities.cache_df('hkjc_jockey_info', 'jockey_id')
    def get_jockey_info(self, web, jockey_id) -> pd.DataFrame:
        
        def restore_jockey_info(ids):
            df = utilities.restore_df('hkjc_jockey_info')
            
            ids = ids[ids != '---']
            
            if 'jockey_id' in df.columns:
                ids_original = ids.copy()
                ids = [val for val in ids if val not in df['jockey_id'].unique()]
                df = df.query('jockey_id in @ids_original')
            utilities.print_msg(f'Pending {len(set(ids))} jockey id(s)...', 'orgtbl') if len(ids) else None
            
            return df, ids
        
        df, jockey_id = restore_jockey_info(jockey_id)
        
        for id in set(jockey_id):
            try:
                web.get(f'{self.__url_jockey}?JockeyId={id}')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_jockey))
                )
            except:
                web.get(f'{self.__url_jockey}?JockeyId={id}&Season=Previous')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_jockey))
                )
            
            content = pd.read_html(
                web.find_element_by_xpath(self.__tag_jockey).get_attribute('outerHTML')
            )[0][0]
            
            season_tab = web.find_element_by_xpath(self.__tag_season_tab).text.split('\n')
            
            df_merge = pd.DataFrame({
                'jockey_id': [id]
                , 'jockey_name': [content[0]]
                , 'jockey_age': re.findall(r'\d{1,3}', content[1])
                , 'jockey_nationality': re.findall(r'Nationality : (\w*)', season_tab[1])
                , 'jockey_last_update': datetime.today().strftime('%Y')
            })
            
            df = pd.concat([df, df_merge], ignore_index = True)
            del content, season_tab, df_merge
        
        return df
    
    @utilities.elapse_time
    @utilities.cache_df('hkjc_horse_info', 'horse_id')
    def get_horse_info(self, web, horse_id) -> pd.DataFrame:
        
        def restore_horse_info(ids):
            df = utilities.restore_df('hkjc_horse_info')
            
            ids = ids[ids != '---']
            
            if 'horse_id' in df.columns:
                ids_original = ids.copy()
                ids = [val for val in ids if val not in df['horse_id'].unique()]
                df = df.query('horse_id in @ids_original')
            utilities.print_msg(f'Pending {len(set(ids))} horse id(s)...', 'orgtbl') if len(ids) else None
            
            return df, ids
        
        df, horse_id = restore_horse_info(horse_id)
        
        for id in set(horse_id):
            try:
                web.get(f'{self.__url_horse}?HorseId={id}')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_horse))
                )
                id_flag = True
            except:
                web.get(f'{self.__url_horse}?HorseNo={id}')
                WebDriverWait(web, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.__tag_horse))
                )
                id_flag = False
            
            content = pd.read_html(
                web.find_element_by_xpath(self.__tag_horse).get_attribute('outerHTML')
            )
            
            tab_1 = content[2].set_axis(['col', ':', 'val'], axis = 1)
            tab_2 = content[3].set_axis(['col', ':', 'val'], axis = 1)
            
            df_merge = pd.DataFrame({
                ['horse_num', 'horse_id'][id_flag]: [id]
                , 'horse_country': re.findall(r'[A-Z]+', tab_1['val'][0])
                , 'horse_age': re.findall(r'\d+', ['0', tab_1['val'][0]]['/' in tab_1['val'][0]])
                , 'horse_colour': [' / '.join(re.findall(r'(\w+) /', tab_1['val'][1]))]
                , 'horse_sex': re.findall(r'/ (\w+)$', tab_1['val'][1])
                , 'horse_import_type': tab_1.query("col == 'Import Type'")['val'].values
                , 'horse_owner': tab_2.query("col == 'Owner'")['val'].values
                , 'horse_sire': tab_2.query("col == 'Sire'")['val'].values
                , 'horse_dam': tab_2.query("col == 'Dam'")['val'].values
                , 'horse_dams_sire': tab_2.query('col == "Dam\'s Sire"')['val'].values
                , 'horse_last_update': datetime.today().strftime('%Y')
            })
            
            df = pd.concat([df, df_merge], ignore_index = True)
            del content, tab_1, tab_2, df_merge
        
        if 'horse_num' in df.columns:
            df['horse_num'] = df['horse_num'].fillna(df['horse_id'])
            df.drop(columns = 'horse_id', inplace = True)
        
        return df
    
    @utilities.elapse_time
    def __get_race_meeting(self, web, race_date, race_no) -> pd.DataFrame:
        if race_date is not None:
            df = self.__get_race_result(web, race_date, race_no)
        else:
            df = pd.DataFrame()
            
            if len(self.__race_date) == 0:
                return None
            
            for date in sorted(self.__race_date):
                utilities.print_msg(f'Waiting for {date}...', 'grid')
                df_merge = self.__get_race_result(web, date, None)
                if df_merge is not None:
                    df = pd.concat([df, df_merge], ignore_index = True)
                utilities.print_msg(f'Finished for {date}!', 'grid')
        
        return df
    
    @utilities.elapse_time
    @utilities.cache_df('hkjc_horse_race', ['race_date', 'index'])
    def query_horse_race_result(self
            , race_date = None, race_no = None, is_addit_info = True) -> pd.DataFrame:
        with webdriver.Chrome('./chromedriver') as web:
            # initialise default settings
            self.__get_default_settings(web)
            
            # main task: scrape race result
            result = self.__get_race_meeting(web, race_date, race_no)
            
            # minor task: scrape trainer, jockey and horse info if valid record and agree from input
            if (result is not None) & (is_addit_info):
                trainer = self.get_trainer_info(web, result['trainer_id'].unique())
                jockey = self.get_jockey_info(web, result['jockey_id'].unique())
                horse = self.get_horse_info(web, result['horse_id'].unique())
                
                df = result \
                    .merge(trainer, on = 'trainer_id', how = 'left') \
                    .merge(jockey, on = 'jockey_id', how = 'left') \
                    .merge(horse, on = 'horse_id', how = 'left')
                
                del result, trainer, jockey, horse
                return df
            
            return result

    @utilities.elapse_time
    def __get_odds_menu(self, web, race_no) -> pd.DataFrame:

        def is_invalid_data(web, race_no) -> bool:
            # avoid input race_no out of bound
            if race_no is not None:
                n_race = web.page_source.count('selectRace')
                if race_no not in range(1, n_race - 1):
                    utilities.print_msg(f'Race No. {race_no} did not exist!', 'simple')
                    return True
            
            return False

        def get_race_info(race_date, race_venue, race_tab) -> pd.DataFrame:
            # race_tab = web.find_element_by_xpath("//div[@style='padding:3px 3px 3px 3px']/div").text
            rt = race_tab.split(', ')
            
            df = pd.DataFrame({
                'race_date': race_date
                , 'race_venue': race_venue
                , 'sec_div_no': re.findall(r'Race (\d+)', rt[0])
                , 'race_class': rt[3]
                , 'distance': re.findall(r'(\d{1,4})[mM]', race_tab)
                , 'going': rt[-1]
                , 'race_name': re.findall(r'Race \d+(.*)', rt[0])
                , 'track': ['ALL WEATHER TRACK', 'TURF']['TURF' in race_tab]
                , 'course': re.findall(r'\"(.*)\"', ['"AWT"', rt[5]]['TURF' in race_tab])
                # , 'pool': re.findall(r'HK\$ ([0-9,]+)', rt[3])
            })
            
            return df
        
        def get_instance_id(html) -> pd.DataFrame:
            html = html.replace(';', '\n')
            
            ids = re.findall(r"goHorseRecord2\(\'(.*)\'\)", html)
            idx_ids = pd.DataFrame({'id': ids}).reset_index()
            
            horse_id = utilities.restore_df('hkjc_horse_info')['horse_id']
            horse_id = horse_id.str.split('_', expand = True) \
                .set_axis(['loc', 'yr', 'id'], axis = 1) \
                .assign(horse_id = horse_id) \
                .query('id in @ids')[['id', 'horse_id']]
            
            idx_ids = idx_ids.merge(horse_id, on = 'id', how = 'left')
            
            df = pd.DataFrame.from_dict({
                'horse_num': list(idx_ids['horse_id'].fillna(idx_ids['id']))
                , 'jockey_id': re.findall(r"goJockeyRecord2\(\'(.*)\'\)", html)
                , 'trainer_id': re.findall(r"goTrainerRecord2\(\'(.*)\'\)", html)
            }, orient = 'index').T.fillna('---')
            
            return df
        
        df = pd.DataFrame()
        
        web.get(self.url_odds)
        WebDriverWait(web, 10).until(
            EC.presence_of_element_located((By.XPATH, self.__odds_date_venue))
        )
        
        # handle unexpected results
        if is_invalid_data(web, race_no):
            return None
        
        # get racing date and venue
        content = web.find_element_by_xpath(self.__odds_date_venue).text
        race_date = re.findall(r'(\d{2,4}/\d{2,4}/\d{2,4})', content)[0]
        race_venue = ['HV', 'ST']['Sha Tin' in content]
        
        race_card = web.page_source.count('selectRace')
        
        for race_idx in range(1, race_card + 1):
            # allocate target race number if defined
            if (race_no is not None) & (race_no != race_idx):
                continue
            
            if race_idx != 1:
                web.find_element_by_xpath(f"//div[@class='raceNoOff_{race_idx}']").click()
            
            WebDriverWait(web, 10).until(
                EC.presence_of_element_located((By.XPATH, self.__odds_race_tag))
            )
            
            # get race details
            race_info = get_race_info(
                race_date, race_venue, web.find_element_by_xpath(self.__odds_race_tag).text
            )
            
            # get individuals id
            instance_id = get_instance_id(
                web.find_element_by_xpath(self.__odds_id).get_attribute('outerHTML')
            )
            
            odds_menu = pd.read_html(
                web.find_element_by_xpath(self.__odds_menu).get_attribute('outerHTML')
            )[0].set_axis(
                ['horse_no', 'colour', 'horse', 'draw', 'actual_weight'
                , 'jockey', 'trainer', 'win_odds', 'place_odds', 'check_box']
                , axis = 1
            )[:-1].drop(columns = ['colour', 'check_box'])
            
            # quick remediation on data type
            odds_menu[['actual_weight', 'draw', 'win_odds', 'place_odds']] = \
                odds_menu[['actual_weight', 'draw', 'win_odds', 'place_odds']].astype(str)
            
            # combine information
            df_merge = pd.concat([race_info, instance_id], axis = 1).fillna(method = 'ffill')
            df_merge = pd.concat([odds_menu, df_merge], axis = 1)
            
            df = pd.concat([df, df_merge], ignore_index = True)
            del race_info, instance_id, odds_menu, df_merge
            
            utilities.print_msg(f'Done for {race_idx} race card!', 'simple') if race_no is None else None
        
        return df

    @utilities.elapse_time
    @utilities.cache_df('hkjc_odds_menu', ['race_date', 'sec_div_no'])
    def query_odds_menu(self, race_no = None, is_addit_info = True) -> pd.DataFrame:
        with webdriver.Chrome('./chromedriver') as web:
            
            # main task: scrape race result
            odds_menu = self.__get_odds_menu(web, race_no)
            
            # minor task: scrape trainer, jockey and horse info if agree from input
            if (odds_menu is not None) & (is_addit_info):
                trainer = self.get_trainer_info(web, odds_menu['trainer_id'].unique())
                jockey = self.get_jockey_info(web, odds_menu['jockey_id'].unique())
                horse = self.get_horse_info(web, odds_menu['horse_num'].unique())
                if 'horse_num' not in horse.columns:
                    horse.rename(columns = {'horse_id': 'horse_num'}, inplace = True)
                
                df = odds_menu \
                    .merge(trainer, on = 'trainer_id', how = 'left') \
                    .merge(jockey, on = 'jockey_id', how = 'left') \
                    .merge(horse, on = 'horse_num', how = 'left')
                
                del odds_menu, trainer, jockey, horse
                return df
            
            return odds_menu

if __name__ == '__main__':
    demo = HongKongJockeyClubHorseRace()
    
    ## case 1: valid input and return result
    #      |  race_date | race_venue | sec_div_no | index | race_class | distance | ... | horse_dams_sire | horse_last_update |
    # |---:|:-----------|:-----------|:-----------|:------|:-----------|:---------|:----|:----------------|:------------------|
    # |  0 | 2022/01/30 |         ST |          1 |   375 |          4 |     1200 | ... |       Strategic |              2022 |
    # |  1 | 2022/01/30 |         ST |          1 |   375 |          4 |     1200 | ... |            Rahy |              2022 |
    # |  2 | 2022/01/30 |         ST |          1 |   375 |          4 |     1200 | ... |    Scaredee Cat |              2022 |
    # |  3 | 2022/01/30 |         ST |          1 |   375 |          4 |     1200 | ... |     King's Best |              2022 |
    demo.query_horse_race_result('2022/01/30', 1)
        
    ## case 2: valid input but the race is hosted oversea
    # Date 2021/10/16 was an oversea race!
    demo.query_horse_race_result('2021/10/16', 2, False)
    
    ## case 3: valid input but the race is abandoned
    # Date 2021/10/13 was an abandoned race!
    demo.query_horse_race_result('2021/10/13', 3, False)

    ## case 4: valid input and return odds menu
    #      |  horse_no |           horse | draw | actual_weight |    jockey |  trainer | ... |  horse_dams_sire | horse_last_update |
    # |---:|:----------|:----------------|:-----|:--------------|:----------|:---------|:----|:-----------------|:------------------|
    # |  0 |         1 |      CHARITY GO |  7.0 |         123.0 |  M F Poon | C S Shum | ... |        Muhtarram |              2022 |
    # |  1 |         1 | DELIGHTFUL LAOS |  3.0 |         123.0 |  K Teetan | A S Cruz | ... |        Tillerman |              2022 |
    # |  2 |         1 |   SUPER FOOTBAL |  5.0 |         123.0 | A Hamelin | K H Ting | ... | Redoute's Choice |              2022 |
    # |  3 |         1 |    BERLIN TANGO |  1.0 |         122.0 |  Z Purton | A S Cruz | ... |   Sadler's Wells |              2022 |
    demo.query_odds_menu(1)