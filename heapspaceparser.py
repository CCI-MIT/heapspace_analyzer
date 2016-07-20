def get_file_contents(path):
    linecount = 0
    import os
    import dateutil.parser
    (target_date_text, target_date) = os.path.basename(path), ""
    try:
        target_date = dateutil.parser.parse(target_date_text).date()
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

        old_gen = content.split("PS Old Generation")
        old_gen_data_rows = old_gen[1].split("\n")
        old_gen_data_rows_split = [[x.strip().split(" ")[0] for x in r.split("=")] for r in
                                   old_gen_data_rows]
        old_gen_data = {r[0]: int(r[1]) / 1024 / 1024 for r in old_gen_data_rows_split if
                        len(r) == 2}

        old_gen_data["file"] = path
        old_gen_data["date"] = target_date
        return old_gen_data
    except Exception as e:
        return {"file": path, "date": target_date, "exception": e, "trivial": linecount < 20,
                "capacity": 0, "used": 0, "free": 0}


def recursively_process_folder(folder_path, prune_errors=True):
    from os import listdir
    contents = [get_file_contents(folder_path + "/" + f) for f in listdir(folder_path)]
    return [c for c in contents if not prune_errors or not "exception" in c]


def prune(n, data_list):
    return [r for index, r in enumerate(data_list) if index < n]


def plot(data_list, outfile="heap.png"):
    import pandas as p
    df = p.DataFrame(data_list).sort("file", ascending=False)
    df.index = df["date"]
    df[["capacity", "used", "free"]].plot(title="heap usage")
    from pylab import savefig, ylabel
    ylabel("MB")
    savefig("%s.png" % outfile, dpi=300)


def archive_older_files_than(top_count, folder_path, archive_directory):
    data = recursively_process_folder(folder_path)
    import pandas as p
    import shutil
    df = p.DataFrame(data).sort("file", ascending=True)
    files_to_be_moved = df["file"][:len(df) - top_count]
    for f in files_to_be_moved:
        shutil.move(f, archive_directory)
    return len(files_to_be_moved)


def weekly(folder_name="heap_big"):
    archive_older_files_than(6 * 24 * 7, "heap_big", "heap_big/archive")
    plot(recursively_process_folder(folder_name, False))


def poll_current(warning_threshold=800, files_to_consider=2, folder_name="heap_big"):
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


poll_current(warning_threshold=420)