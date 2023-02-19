import os, json, vmdata
from flask import Flask, jsonify, render_template, request, redirect, session, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, Email
from datetime import timedelta
from cachelib.simple import SimpleCache
import pandas as pd


app = Flask(__name__)

app.config['SECRET_KEY'] = "super_secret"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

cache = SimpleCache()

class FileUploadForm(FlaskForm):
    file = FileField(validators=[DataRequired()])

@app.route('/', methods=['GET', 'POST'])
def index():
    form = FileUploadForm()
  
    if form.validate_on_submit():
        session['filename'] = form.file.data.filename
        session['path'] = 'uploads/' + session['filename']
        form.file.data.save(session['path'])

        # load df and meta into cache
        df, meta = vmdata.get_rvtools_data(session['path'])
        cache.set('df', df, timeout=None)
        cache.set('meta', meta, timeout=None)

        #Delete the file
        os.remove(session['path'])
        
        return redirect(url_for('summary'))

    return render_template('index.html', form=form)

@app.route('/summary', methods=['GET','POST'])
def summary():
    df = cache.get('df')
    meta = cache.get('meta')
  
    if df is None or meta is None:
        return redirect(url_for('index'))
  
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
    # Read data from cache or get it from the database
    df = cache.get('df')
    if df is None:
        return redirect(url_for('index'))
    else:
        # Update data in cache based on changes from /update-row route
        updated_data = request.args.get('updated_data')
        if updated_data:
            updated_data = json.loads(updated_data)
            row_index = updated_data['row_index']
            updated_row = updated_data['row_data']
            df.at[row_index, 'Exclude'] = updated_row['Exclude']
            cache.set('df', df)

    # Convert the Pandas dataframe to a dictionary
    data = df.to_dict('records')
    
    return render_template('vmlist.html', data=data)

# define the route to update the row in the data variable
@app.route('/update-row', methods=['POST'])
def update_row():
    # get the row data from the request body
    row_data = request.get_json()
    df = cache.get('df')
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

    # update the cache with the modified dataframe
    df = pd.DataFrame(data)
    cache.set('df', df, timeout=None)
  
    # return a JSON response indicating success
    return jsonify({'success': True, 'changed_data': changed_data})

@app.errorhandler(404)
def page_not_found(error):
    '''
    Function to render the 404 error page
    '''
    return render_template('404.html'),404
  
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81, debug = True)