from flask import Flask, render_template, url_for, request, session, redirect
import pymysql
import face_recognition as fr
import os
import cv2
import face_recognition
import numpy as np
from time import sleep
import datetime
from werkzeug.utils import secure_filename
import xlsxwriter
import traceback


def get_encoded_faces():
    encoded = {}

    for dirpath, dnames, fnames in os.walk("./faces"):
        for f in fnames:
            if f.endswith(".jpg") or f.endswith(".png"):
                face = fr.load_image_file("faces/" + f)
                encoding = fr.face_encodings(face)[0]
                encoded[f.split(".")[0]] = encoding

    return encoded


def unknown_image_encoded(img):
    face = fr.load_image_file("faces/" + img)
    encoding = fr.face_encodings(face)[0]

    return encoding


def classify_imgae(im):
    faces = get_encoded_faces()
    faces_encoded = list(faces.values())
    known_face_names = list(faces.keys())

    img = cv2.imread(im, 1)

    face_locations = face_recognition.face_locations(img)

    unknown_face_encodings = face_recognition.face_encodings(img, face_locations)
    face_names = ""
    for face_encoding in unknown_face_encodings:
        matches = face_recognition.compare_faces(faces_encoded, face_encoding)
        name = "unknown"

        face_distances = face_recognition.face_distance(faces_encoded, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        face_names = name

    while True:
        return face_names


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
app.config['UPLOAD_FOLDER'] = 'faces'


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/student_login_old", methods=['GET', 'POST'])
def student_login_old():
    flag = 0
    if (request.method == 'POST'):
        uname = request.form.get('uname')
        pwd = request.form.get('password')

        print(f'Received from front end : uname : {uname}, pwd : {pwd}')

        try:

            db = pymysql.connect(host='127.0.0.1',
                                 user='root',
                                 password='admin',
                                 db='facerecognition',
                                 autocommit=True)
            cursor = db.cursor()
            # q1 = "SELECT * FROM students NATURAL JOIN stud_reg_courses WHERE reg_no=%s"
            # q1 = "SELECT * FROM students NATURAL JOIN students WHERE reg_no=%s"
            q1 = "SELECT * FROM students WHERE reg_no=%s"
            cursor.execute(q1, (uname))
            global results
            results = cursor.fetchall()
            print(results)
            db.close()
            if (pwd == results[0][4]):
                session['username'] = uname

                return render_template('take_attendance.html', results=results)

            else:
                return "Incorrect password"

        except Exception as e:
            print(traceback.format_exc())
            flag = 0
            print("NO results found!")
            print(e)

    else:
        return "Please Sign Up First"
    return "PLEASE SIGN UP FIRST!!"


@app.route("/student_login", methods=['GET', 'POST'])
def student_login():
    flag = 0
    if (request.method == 'POST'):
        uname = str(request.form.get('uname'))
        pwd = str(request.form.get('password'))

        print(f'Received from front end : uname : {uname}, pwd : {pwd}')

        try:

            connection = pymysql.connect(host='127.0.0.1',
                                         user='root',
                                         password='admin',
                                         db='facerecognition',
                                         # charset='utf8mb4',
                                         # cursorclass=pymysql.cursors.DictCursor,
                                         autocommit=True)

            with connection:

                with connection.cursor() as cursor:
                    # Read single student record
                    # only reg_no we have in db : 2020ITB05
                    # sql = "SELECT `password` FROM `students` WHERE `reg_no`=%s"
                    sql = "SELECT * FROM `students` WHERE `reg_no`=%s"

                    cursor.execute(sql, (uname,))
                    result = cursor.fetchone()
                    print(f'result from database :  {result}')
                    # pwd_db = result['password']
                    pwd_db = result[4]

            if pwd == pwd_db:

                session['username'] = uname

                return render_template('take_attendance.html', results=result)

            else:
                return "Incorrect password"

        except Exception as e:
            print(traceback.format_exc())
            flag = 0
            print("NO results found!")
            print(e)

    else:
        return "Please Sign Up First"
    return "PLEASE SIGN UP FIRST!!"


@app.route("/student_signup", methods=['GET', 'POST'])
def student_signup():
    # inserting data into database
    try:
        db = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             db='project')
        if (request.method == 'POST'):
            reg_no = request.form.get('reg_no')
            name = request.form.get('name')
            email = request.form.get('email')
            contact_no = request.form.get('contact_no')
            pwd = request.form.get('pwd')
            pic1 = request.files['pic1']
            pic2 = request.files['pic2']
            pic3 = request.files['pic3']

            fn1 = secure_filename(pic1.filename)
            print(fn1)
            pic1.save(os.path.join(app.config['UPLOAD_FOLDER'], fn1))

            fn2 = secure_filename(pic2.filename)
            pic2.save(os.path.join(app.config['UPLOAD_FOLDER'], fn2))

            fn3 = secure_filename(pic3.filename)
            pic3.save(os.path.join(app.config['UPLOAD_FOLDER'], fn3))

            print("All images saved")

            print("writing in DB")
            cursor = db.cursor()
            sql = "INSERT INTO students VALUES(%s,%s,%s,%s,%s)"
            cursor.execute(sql, (reg_no, name, email, contact_no, pwd))
            db.commit()
            msg = "Your Account Created Successfully"
            return render_template('home.html', msg=msg)
            db.close()
        else:
            return "Problem in inserting data"

    except Exception as e:
        print(e)

    return "not done"


@app.route("/attendance")
def attendance():
    os.system('python take_pic.py')
    attndee = classify_imgae("test.jpg")
    attndee = attndee[0:9]
    current_time = datetime.datetime.now()
    time = current_time.hour + current_time.minute
    workbook = xlsxwriter.Workbook('attendance_sheet.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write('A1', 'reg_no')
    worksheet.write('B1', 'time')
    worksheet.write('A2', attndee)
    worksheet.write('B2', current_time)
    workbook.close()

    return render_template('take_attendance.html', attndee=attndee)


@app.route("/log_out")
def log_out():
    session.clear()
    return render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True)