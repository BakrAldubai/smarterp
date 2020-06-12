import pandas as pd
import numpy as np
import datetime
import csv
import json

class Combiner:
    def __init__(self, path):
        self.assignments = None
        self.domain_by_customer = None
        self.customer_by_domain = None
        self.metrics = None
        self.todo_owners = None

        self.path = path

    def extract_domain(self,email):
        mail_split = email.split("@")
        if(len(mail_split) > 1):
            return mail_split[1]
        else:
            return email

    def samples_enrich(self, samples):        
        #Extract customer's domain from raised_by field
        samples.loc[:,"domain"] = samples.loc[:,"raised_by"].apply(self.extract_domain)

        #Convert datatypes
        dt_cols = ["creation", "modified"]
        for col in dt_cols:
            samples[col] = pd.to_datetime(samples[col], format="%Y-%m-%d %H:%M:%S.%f")

        #Add Day of week, when issue was created
        samples.loc[:,"day_of_week"] = samples.loc[:,"creation"].dt.weekday

        #Add Year, when issue was created
        samples.loc[:,"year"] = samples.loc[:,"creation"].dt.strftime("%Y")

        #Add calendar week
        samples.loc[:,"calendar_week"] = samples.loc[:,"creation"].dt.weekofyear

        #Add a start_date
        samples["start_date"] = samples["creation"].dt.strftime("%Y-%m-%d")

        return samples 

    def create_domain_mappings(self, contacts):

        #Extract customer's domain from email_ids
        contacts.loc[:,"email_ids"] = contacts.loc[:,"email_ids"].astype(str)
        mail_split = contacts.loc[:,"email_ids"].str.split(pat = "@",expand=True)
        contacts.loc[:,"domain"] = mail_split.loc[:,1]

        #Uniquely group by customer and domain
        mapping = contacts.loc[:,["customer","domain","name"]]
        mapping = mapping.dropna(subset=["customer","domain"],axis="rows").sort_values("customer")
        mapping = mapping.groupby(["customer","domain"],as_index=False)["name"].count()
        mapping = mapping.rename(columns={"name": "contact count"}).sort_values("contact count",ascending=False)

        #The problem customers have multiple domains -> Take the domain with the highest contact count
        customers = mapping["customer"].unique().tolist()
        domain_by_customer = {}
        customer_by_domain = {}
        for customer in customers:
            max_contacts = mapping.loc[mapping["customer"] == customer,"contact count"].max()
            is_customer = mapping["customer"] == customer
            is_max_contacts = mapping["contact count"] == max_contacts
            is_best_domain = mapping.loc[(is_customer & is_max_contacts),"domain"].iloc[0]
            domain_by_customer[customer] = is_best_domain
            customer_by_domain[is_best_domain] = customer
            #print("Customer: " + customer + " Datatype: " + str(type(customer)) + " Domain: " + is_best_domain)

        self.domain_by_customer = domain_by_customer
        self.customer_by_domain = customer_by_domain

    def samples_map_domains(self, samples):
        samples = samples.copy()

        #Map customer to domain
        is_tueit = samples["domain"] == "tueit.de"
        samples.loc[(is_tueit),"domain"] = samples.loc[(is_tueit),"customer"].map(self.domain_by_customer)

        #Map domain to customer (This potentially creates NaN's in customer...)
        is_foreign_domain = samples["domain"] != "tueit.de" 
        customer_missing = (samples["customer"] == "00062") | (samples["customer"].isna())
        samples.loc[(is_foreign_domain & customer_missing),"customer"] = samples.loc[(is_foreign_domain & customer_missing),"domain"].map(self.customer_by_domain)
        
        return samples

    def process_samples(self, samples):
        #Adding everything to the sample
        print("Shape of samples before processing: " + str(samples.shape))
        samples = self.samples_enrich(samples)
        samples = self.samples_map_domains(samples)
        samples = self.lookup_metrics(samples)
        print("Shape of samples after processing: " + str(samples.shape))

        return samples

    def set_assignments(self, issues, todos, contacts):
        
        assignments = pd.merge(todos.add_prefix("todo_"),issues, left_on="todo_reference_name", right_on="name", how="left")       
        
        assignments = self.samples_enrich(assignments)
        self.create_domain_mappings(contacts)
        assignments = self.samples_map_domains(assignments)
        self.assignments = assignments
        employees = assignments["todo_owner"].unique()
        self.todo_owners = employees[~pd.isnull(employees)].tolist() #Removes nans
    

    def set_timesheets(self, timesheets, employees, projects, customers):

        #Add customer from the issues
        print("Combiner: Adding customer from issues.")
        assignments = self.assignments.rename(columns={"name": "issue"})
        timesheets = pd.merge(timesheets, assignments.loc[:,["issue","customer"]], on="issue", how="left")

        #Add Employee id (user_id)
        print("Combiner: Adding user_id to Assignments.")
        employees = employees.rename(columns={"name" : "employee"})
        timesheets = timesheets.merge(employees,on="employee",how="left")

        #Add Project
        print("Combiner: Adding project to Assignments.")
        projects = projects.rename(columns={"name" : "project"})
        timesheets = pd.merge(timesheets,projects,on="project",how="left", suffixes=("_from_issues","_from_projects"))

        #Add Customer
        print("Combiner: Adding customer to Assignments.")
        timesheets = timesheets.drop("customer_name",axis=1)
        customers = customers.rename(columns={"name" : "customer"})
        timesheets["customer"] = np.where((timesheets["customer_from_issues"].isnull()),timesheets["customer_from_projects"],timesheets["customer_from_issues"])
        timesheets = timesheets.drop("customer_from_issues", axis=1)
        timesheets = timesheets.drop("customer_from_projects", axis=1)
        timesheets = pd.merge(timesheets,customers, on="customer", how="left")
       

        #Basic transformation
        timesheets["start_date"] = pd.to_datetime(timesheets["start_date"])
        timesheets = timesheets.groupby(["start_date","user_id","customer"],as_index=False)["total_hours"].sum()
        timesheets = timesheets.sort_values("start_date", ascending=True).reset_index(drop=True)

        #Expand by x days
        print("Combiner: Expanding timesheets by 8 days.")
        last_date = timesheets.iloc[len(timesheets) - 1, 0]
        for i in range(1,8):
            day_ahead = last_date + datetime.timedelta(days=i)
            timesheets = timesheets.append({'start_date': day_ahead, 'customer' : "dummy", 'user_id' : "dummy", 'total_hours' : 0}, ignore_index=True)

        #Create Pivot
        print("Combiner: Pivoting timesheets.")
        timesheets = timesheets.loc[:,["start_date","user_id","customer","total_hours"]]
        timesheets = timesheets.pivot_table(index="start_date", columns=["user_id","customer"]).fillna(0)

        #Compute metrics
        print("Combiner: Compute metrics.")
        self.init_timesheet_metrics(timesheets)

        #Apply metrics
        self.assignments = self.lookup_metrics(self.assignments)

    def init_timesheet_metrics(self,ts_pp):
        

        metrics = {}
        metrics["avg10"] = ts_pp.rolling(10, win_type=None).mean().shift(1).fillna(0.0)
        metrics["avg30"] = ts_pp.rolling(30, win_type=None).mean().shift(1).fillna(0.0)
        metrics["std30"] = ts_pp.rolling(30, win_type=None).std().shift(1).fillna(0.0)


        self.metrics = metrics

    def add_metric(self, base, metric, prefix):
        idx = pd.IndexSlice
        #metrics.loc[:,idx["total_hours","thomas.kopp@tueit.de","00002"]]
        employees = self.todo_owners
        df_metrics_pivot = []
        df_index =[]
        for index, row in base.iterrows():
        #row = im.loc[30]#
            #print(row)
            date = row["start_date"]
            customer = row["customer"]
            metrics_row = []
            df_index.append(date)
            for e in employees:#e = "marius.widmann@tueit.de"#
                #print("Employee: " + e + ", Date: " + str(date))
                metric_col = []
                if(metric.index.dtype == 'object'): dates = pd.to_datetime(metric.index).strftime("%Y-%m-%d").tolist()
                elif(metric.index.dtype == 'datetime64'): dates = metric.index.strftime("%Y-%m-%d").tolist()
                else: dates = metric.index.strftime("%Y-%m-%d").tolist()
                #print(dates)
                has_date = date in dates
                found_value = False
                if(has_date):
                    #print("Has date.")
                    #print(metrics.loc[date,idx["total_hours"]])
                    col_names = metric.loc[date,idx["total_hours",:,:]].index.tolist()
                    indices = [x[1] for x in col_names]
                    has_employee = e in indices
                    if(has_employee):
                        #print("Has employee: "+ e)
                        col_names = metric.loc[date,idx["total_hours",e]].index.tolist()
                        has_customer = customer in col_names
                        #if(e == "wolfram.schmidt@tueit.de" and c == "00062" and date == "03.01.2020"):
                        #    print("foudn")
                        if(has_customer):
                            #print("Has customer: "+ customer)
                            found_value = True
                            value = metric.loc[date,idx["total_hours",e,customer]]
                            metrics_row.append(float(value))
                            #print("Added value: " + str(type(value)))
                            #print(str(value))
                if(not found_value):
                    metrics_row.append(0.0)
                    #print("Imputed value: " + str(type(0.0)))
            #print((metrics_row))
            df_metrics_pivot.append(metrics_row)
        
        #Creating the dataframe
        col_names = employees
        df = pd.DataFrame(index=df_index,data=df_metrics_pivot,columns=col_names).add_prefix(prefix)
        df = df.reset_index(drop=True)
        base = base.reset_index(drop=True)
        combined = pd.concat([base,df],sort=False,axis=1)  #TODO ignore_index ?
        
        return combined

    def lookup_metrics(self, samples):
        #Prepare base data for metrics adding
        #print(self.assignments.info())
        base = samples.sort_values("start_date").reset_index(drop=True).copy()
        
        metrics = self.metrics
        for key,df in metrics.items():
            metric = df
            base = self.add_metric(base,metric,key + "_")
        
        return base

    def save(self):
        #Save assignments
        self.assignments.to_csv(self.path + 'preprocessed.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)

        #Save metrics
        keylist = []
        for key, df in self.metrics.items():
            df.to_csv(self.path + 'metric_' + key + '.csv')
            keylist.append(key)
        with open(self.path + "metricskeys.json", mode="w") as f:
            f.write(json.dumps(keylist))
        
        #Save mappings
        with open(self.path + "customer_by_domain.json", mode="w") as f:
            f.write(json.dumps(self.customer_by_domain))

        with open(self.path + "domain_by_customer.json", mode="w") as f:
            f.write(json.dumps(self.domain_by_customer))
        
        #Save unique todo_owners
        with open(self.path + "todo_owners_unique.json", mode="w") as f:
            f.write(json.dumps(self.todo_owners))

    def load(self):
        self.assignments = pd.read_csv(self.path + 'preprocessed.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')

        keylist = []
        self.metrics = {}
        with open(self.path + "metricskeys.json", mode="r") as f:
            keylist = json.loads(f.read())
        for key in keylist:
            self.metrics[key] = pd.read_csv(self.path + "metric_" + key + ".csv",dtype=object, index_col=[0],header=[0,1,2], skipinitialspace=True)

        with open(self.path + "customer_by_domain.json", mode="r") as f:
            self.customer_by_domain = json.loads(f.read())

        with open(self.path + "domain_by_customer.json", mode="r") as f:
            self.domain_by_customer = json.loads(f.read())

        with open(self.path + "todo_owners_unique.json", mode="r") as f:
            self.todo_owners = json.loads(f.read())