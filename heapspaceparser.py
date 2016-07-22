def parse_filename_to_datetime(filename):
    import dateutil.parser
    exploded = filename.split("-")
    (months, days) = exploded[:3], exploded[3:6]
    targetTime = "-".join(months) + " " + ":".join(days)
    return dateutil.parser.parse("%s" % targetTime)


def get_file_contents(path):
    linecount = 0
    import os
    (target_date_text, target_date) = os.path.basename(path), ""
    try:
        target_date = parse_filename_to_datetime(target_date_text)
    except:
        pass

    try:
        f = open(path, "r")
        content = f.read()
        linecount = len(content.split("\n"))
        f.close()

        # lots of blabla before the last block, which we are mostly interested in:
        # PS Old Generation
        # capacity = 560463872 (534.5MB)
        # used     = 234462504 (223.60086822509766MB)
        # free     = 326001368 (310.89913177490234MB)

        old_gen_data = extract_heap_generation(content, "PS Old Generation")

        old_gen_data["file"] = path
        old_gen_data["date"] = target_date
        return old_gen_data
    except Exception as e:
        return {"file": path, "date": target_date, "exception": e, "trivial": linecount < 20,
                "capacity": 0, "used": 0, "free": 0}


def extract_heap_generation(content, generation_name, prefix=""):
    old_gen = content.split(generation_name)
    old_gen_data_rows = old_gen[1].split("\n")
    old_gen_data_rows_split = [[x.strip().split(" ")[0] for x in r.split("=")] for r in
                               old_gen_data_rows[:4]]
    old_gen_data = {r[0]: int(r[1]) / 1024 / 1024 for r in old_gen_data_rows_split if
                    len(r) == 2}
    #return {(prefix + l): r for l, r in old_gen_data}
    return old_gen_data


def recursively_process_folder(folder_path, prune_errors=True):
    from os import listdir
    contents = [get_file_contents(folder_path + "/" + f) for f in listdir(folder_path)]
    return [c for c in contents if not prune_errors or not "exception" in c]


def plot(data_list, plot_name="heap usage", outfile="heap.png"):
    import matplotlib
    matplotlib.use('Agg')
    import pandas as p
    df = p.DataFrame(data_list).sort("file", ascending=False)
    df.index = df["date"]
    df[["capacity", "used", "free"]].plot(title=plot_name)
    from pylab import savefig, ylabel
    ylabel("MB")
    savefig(outfile, dpi=300)


def archive_older_files_than(days, folder_path, archive_directory):
    data = recursively_process_folder(folder_path, prune_errors=False)
    import pandas as p
    import shutil
    import datetime as DT
    import os
    today = DT.date.today()
    one_week_ago = today - DT.timedelta(days=days)

    def move_files(files):
        for f in files:
            target_filename = archive_directory + "/" + os.path.basename(f)
            if os.path.exists(target_filename):
                print("%s exists, replacing it." % target_filename)
                try:
                    os.remove(target_filename)
                except:
                    pass
            shutil.move(f, archive_directory)

    df = p.DataFrame(data)

    df["dated"] = [d.date() if d is not None else None for d in df["date"]]
    files_with_correct_date = df[df["dated"] < one_week_ago]["file"]
    files_with_exceptions = [f["file"] for f in data if "exception" in f]

    move_files(files_with_correct_date)
    move_files(files_with_exceptions)

    return len(files_with_correct_date) + len(files_with_exceptions)


def weekly(folder_name="example_data", target_folder="archive", plot_name="heap usage", plot_outfile="plot.png"):
    archive_older_files_than(10, folder_name, target_folder)
    plot(recursively_process_folder(folder_name, False), plot_name, plot_outfile)


def poll_current(warning_threshold=800, files_to_consider=2, folder_name="example_data"):
    data = recursively_process_folder(folder_name, False)
    import pandas as p
    df = p.DataFrame(data).sort("file", ascending=False)
    for used in df["used"][:files_to_consider]:
        if (used > warning_threshold):
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText("reached memory threshold: %s" % used)
            msg["Subject"] = "Memory warning"
            me = "balaur@balaur.mit.edu"
            msg["From"] = me
            msg["To"] = "pdeboer@mit.edu"
            s = smtplib.SMTP("localhost")
            s.sendmail(me, "pdeboer@mit.edu", msg.as_string())
            print("sent warning")
