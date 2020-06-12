from smarterp.assigner.combiner import Combiner
from smarterp.assigner.scraper import Scraper
from smarterp.assigner.learner import Learner

import csv
import pandas as pd
import json
import os
import frappe

from frappe.utils import get_site_base_path

from frappe.utils.background_jobs import enqueue
    


class AutoAssigner:
    def __init__(self, site_path = None):
        print("Init AutoAssigner")
        if(site_path == None):
            site_path = get_site_base_path()[2:] + "/"
        scraper_folder = site_path + "assigner/scrapes/"
        combiner_folder = site_path + "assigner/data/"
        learner_folder = site_path + "assigner/model/"
        self.s = Scraper(scraper_folder)
        self.c = Combiner(combiner_folder)
        self.l = Learner(learner_folder)
        print("Initialized")
        #Create folders if not exist
        #if not os.path.exists("assigner"):
        #    os.makedirs("assigner")

        if not os.path.exists(scraper_folder):
            os.makedirs(scraper_folder)

        if not os.path.exists(combiner_folder):
            os.makedirs(combiner_folder)

        if not os.path.exists(learner_folder):
            os.makedirs(learner_folder)

    #Scarpes all necessary doctypes
    def scrape(self, username = None, pwd = None, baseurl = None):
        print("AutoAssigner: Start scraping")
        if(username == None or pwd == None or baseurl == None):
            settings = frappe.get_doc("Settings Smarterp","Settings Smarterp")
            pwd = frappe.utils.password.get_decrypted_password("Settings Smarterp","Settings Smarterp",fieldname="administrator_password")
            self.s.scrape(settings.administrator_username, pwd,settings.baseurl)
        else:
            self.s.scrape(username, pwd, baseurl)
        self.s.save()

    #Combines the doctypes, creates the timesheets lookup table and creates the assignment dataset with timesheet metrics
    def combine(self):
        self.s.load()
        
        self.c.set_assignments(self.s.issues,self.s.todos, self.s.contacts)
        self.c.set_timesheets(self.s.timesheets, self.s.employees, self.s.projects, self.s.customers)
        self.c.save()
        
    #Cross validation for debugging
    def cross_val(self):
        self.c.load()
        self.l.rf_cross_val(self.c.assignments)

    #Train based on assignment dataset
    def train(self):
        self.c.load()
        self.l.train_rf(self.c.assignments)
        print("Saving model...")
        self.l.save()

    #Predict based on an issue
    def predict(self, samples):
        self.l.load()
        self.c.load()
        #Load sample
        #with open("sample.json", mode="r") as f:
        #    j = json.loads(f.read())
        #    j = j["data"]
        #sample = pd.io.json.json_normalize(json)

        #Process
        samples = self.c.process_samples(samples)
        #Optionally for debugging save the last processed sample
        #samples.to_csv("last_sample_enriched.csv", sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)

        #Predict
        assignments_probs = self.l.predict_rf(samples)
        return assignments_probs

def cross_val():
    aa = AutoAssigner()
    aa.cross_val()

@frappe.whitelist()
def get_probabilities(data):
    data = json.loads(data)
    aa = AutoAssigner()
    doc = json.loads(data["frm"])
    samples = pd.DataFrame([doc])
    result = aa.predict(samples)
    return result

@frappe.whitelist()
def prepare_assigner(username = None, pwd = None, baseurl = None, site = None):
    print("Preparing Assigner")
    try:
        aa = AutoAssigner(site)
        print("Initiate scraping.")
        aa.scrape(username, pwd, baseurl)
        print("Initiate combining.")
        aa.combine()
        print("Initiate training.")
        aa.train()
        return "Model is trained"

    except Exception as e:
        return str(e)

#Experimental
@frappe.whitelist()
def prepare_assigner_as_job():
    try:
        enqueue('smarterp.assigner.autoassign.prepare_assigner', timeout=None, queue="long", job_name="Prepare AutoAssigner")
        return "Job successfully started."
    except Exception as e:
     return str(e)

if __name__ == '__main__':
    os.chdir("/home/marius/bench/frappe-bench/sites/")
    prepare_assigner("Administrator", "password", "baseurl", "site_name/")