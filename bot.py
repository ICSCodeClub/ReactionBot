import itertools
import discord
import emojis
import re
import nlp_analysis

import yaml
try: from yaml import CLoader as Loader
except ImportError: from yaml import Loader

# load the config
config = dict()
with open('./config-actual.yml') as file:
    yml = yaml.load(file.read(), Loader=Loader)
    try:
        config['token'] = yml['Token']
        config['reactions'] = yml['Use Reactions']
        config['aliases'] = yml['Aliases']
    except KeyError: 
        print('Error in config')
        quit(1)
    assert '<TOKEN>' not in repr(config), 'Please add your token to the config!'

# setting up the bot, with its discritpion etc.
bot = discord.Client() # use Client, as we don't need full bot functionality

emoji_dict = emojis.db.get_emoji_aliases()
for alias, val in config['aliases'].items():
    if alias.count(':') != 2: alias = ':{}:'.format(alias.replace(':',''))
    if val.count(':') != 2: val = ':{}:'.format(val.replace(':',''))
    
    if val in emoji_dict:
        emoji_dict[alias] = emoji_dict[val]
    else:
        print('Alias {} for {} not found'.format(alias, val))
print('Successfully loaded {} aliases'.format(len(emoji_dict)-len(emojis.db.get_emoji_aliases())))

@bot.event
async def on_ready():
    print('\n\nI am ready to stand beside my warriors again\n\n')

# for every message it does these checks
@bot.event
async def on_message(message):
    text = re.sub(r'\s+',' ', re.sub(r':.*:','', emojis.decode(message.content)).replace('\n',' '))
    # list all emojis
    emoji_list = [str(em).strip(':').replace('_',' ') for em in itertools.chain([x.name for x in message.guild.emojis], emoji_dict.keys())]
    found_ems = list()
    
    for nouns in nlp_analysis.get_noun_phrases(text):
        dist = nlp_analysis.get_min_edit_distance(nouns, emoji_list, length_dependant=True)
        if dist[1] <= 0.2: 
            found_ems.append(dist[0])
        else:
            for word in nouns.split(' '):
                dist = nlp_analysis.get_min_edit_distance(word, emoji_list, length_dependant=True)
                if dist[1] <= 0.2: found_ems.append(dist[0])

    print('Found {0} emojis in message "{1}": {2}'.format(len(found_ems), text, found_ems))

    if len(found_ems) < 5:
        msg = ''
        for em in found_ems:
            if ':{0}:'.format(em.replace(' ','_')) in emoji_dict:
                em = emoji_dict[':{0}:'.format(em.replace(' ','_'))]
                if config['reactions']: await message.add_reaction(em)
                else: msg = '{0}{1}'.format(msg, em)
            else: # server emoji
                if config['reactions']: 
                    for server_emote in message.guild.emojis:
                        if server_emote.name.lower() != em.lower(): continue
                        await message.add_reaction(server_emote)
                        break
                else: msg = '{0}{1}'.format(msg, ':{0}:'.format(em))
        if not config['reactions']:
            await message.guild.send(msg)

bot.run(config['token'])

