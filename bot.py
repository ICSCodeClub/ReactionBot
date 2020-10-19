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
with open('./config.yml') as file:
    yml = yaml.load(file.read(), Loader=Loader)
    try:
        config['token'] = yml['Token']
        config['reactions'] = yml['Use Reactions']
        config['aliases'] = yml['Aliases']
        config['thresh'] = float(yml['Recognition Threshold'])
        config['limits'] = (int(yml['Minimum Emotes']), int(yml['Maximum Emotes']))
        config['min'] = int(yml['Minimum Word Length'])
    except (KeyError, ValueError): 
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
    
    # detect all reactions
    found_ems = list()

    for nouns in nlp_analysis.get_noun_phrases(text):
        if len(nouns) < config['min']: continue
        dist = nlp_analysis.get_min_distance(nouns, emoji_list)
        if dist[1] <= config['thresh']: 
            found_ems.append((nouns,)+dist)
            text = text.replace(nouns,'') # more duplicate prevention
    for word, pos in nlp_analysis.tag_pos(text):
        if len(word) < config['min']: continue
        if pos == None: continue # force part of speech detection
        dist = nlp_analysis.get_min_distance(word, emoji_list,pos=pos)
        if dist[1] <= config['thresh']: found_ems.append((word,)+dist)

    # remove duplicates
    i = len(found_ems)-1
    while i >= 0:
        if found_ems[i][1] in [found_ems[x][1] for x in range(len(found_ems)) if x != i]:
            found_ems.pop(i)
        i -= 1
    
    # print emojis found
    if len(found_ems) > 0: print('Found {0} emojis in message "{1}": {2}'.format(len(found_ems), str(message.content).replace('\n',' '), found_ems))

    # add the reactions
    if config['limits'][0] <= len(found_ems) <= config['limits'][1]:
        msg = ''
        for em in found_ems:
            em = em[1]
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
                else: msg += str(discord.utils.get(bot.emojis, name=em))
        if not config['reactions']:
            await message.channel.send(msg)

bot.run(config['token'])