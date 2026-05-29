{
    "name": "Birthday Wishes",
    "summary": "Birthday Wishes For an Employee",
    "version": "17.0.1.0.1",
    "category": "Human Resources",
    "author":"Penygonarabia",
    "depends": ["hr","base","mail","web"],
    
    "data": [
                "data/wish_schedule.xml",
                # "views/employee_wish_template.xml",
             ],
    'assets': {     
        'web.assets_common': [ 
            'birthday_wish/static/src/img/*', ], 
        
        },
 
    "installable": True,
}
