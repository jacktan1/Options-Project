import os


# MAKE SURE NOT TO RUN THIS MULTIPLE TIMES, FUNCTION DOES NOT CHECK IF FILE HAS ALREADY
# BEEN RENAMED!

def listdir_nohidden(path):
    my_list = []
    for f in os.listdir(path):
        if not f.startswith('.'):
            my_list.append(f)
    return my_list


def listfile_nohidden(path):
    my_list = []
    for f in os.listdir(path):
        if not f.startswith('.'):
            if os.path.isfile(os.path.join(path, f)):
                my_list.append(f)
    return my_list


my_path = 'backtest_data/'
first = os.listdir(my_path)

for n in first:
    second = listdir_nohidden(str(my_path + n))
    for m in second:
        onlyfiles = listfile_nohidden(str(my_path + n + '/' + m))
        for nn in onlyfiles:
            os.rename(str(my_path + n + '/' + m + '/' + nn),
                      str(my_path + n + '/' + m + '/' + nn[0:4] + '-' + nn[4:6] + '-' + nn[6:]))

print('nani')
