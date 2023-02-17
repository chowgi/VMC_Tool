from flask import Flask, jsonify, render_template, request, redirect, session, url_for
import os, json, vmdata
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, Email
from flask_paginate import Pagination, get_page_args, get_page_parameter

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

class FileUploadForm(FlaskForm):
    file = FileField(validators=[DataRequired()])

@app.route('/', methods=['GET', 'POST'])
def index():
    form = FileUploadForm()
  
    if form.validate_on_submit():
        session['filename'] = form.file.data.filename
        session['path'] = 'uploads/' + session['filename']
        form.file.data.save(session['path'])
        
        return redirect(url_for('details'))

    return render_template('index.html', form=form)

@app.route('/summary', methods=['GET','POST'])
def details():
    df, meta = vmdata.get_rvtools_data(session['path'])
    #os.remove(session['path'])
    totals = vmdata.all_resources(df)
    cpu = vmdata.top_cpu(df)
    memory = vmdata.top_memory(df)
    os_consumed = vmdata.top_os_consumed(df)
    meta = meta.to_dict('records')
    filename = session['filename']
    #check how many clusters. If more than one render a page with the cluster detials
    cluster_count = df['Cluster'].unique().tolist()
    if len(cluster_count) > 1:
        clusters = vmdata.grouped_by(df, 'Cluster')
        return render_template("summary.html",
                               totals=totals,
                               cpu=cpu, 
                               memory=memory, 
                               os_consumed=os_consumed, 
                               clusters=clusters, 
                               meta=meta, 
                               filename=filename)
    else:
        return render_template("summary.html", 
                               totals=totals, 
                               cpu=cpu, 
                               memory=memory, 
                               os_consumed=os_consumed, 
                               meta=meta, 
                               filename=filename)

@app.route('/vmlist')
def vmlist():
    # Read data into a Pandas dataframe
    df, _ = vmdata.get_rvtools_data(session['path'])
    
    # Convert the Pandas dataframe to a dictionary
    data = df.to_dict('records')
    
    return render_template('vmlist.html', data=data)

# define the route to update the row in the data variable
@app.route('/update-row', methods=['POST'])
def update_row():
  # get the row data from the request body
  row_data = request.get_json()
  df, _ = vmdata.get_rvtools_data(session['path'])
  data = df.to_dict('records')
  print("row", request.get_json())
  changed_data = {}
  # update the row in the data variable
  for i, vm in enumerate(data):
    if vm['VM'] == row_data['name']:
      data[i]['Exclude'] = row_data['Exclude']
      changed_data = data[i]
      print("data[i]", data[i])
      break

  # return a JSON response indicating success
  print('boom!')
  return jsonify({'success': True, 'changed_data': changed_data})

@app.errorhandler(404)
def page_not_found(error):
    '''
    Function to render the 404 error page
    '''
    return render_template('404.html'),404
  
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81, debug = True)