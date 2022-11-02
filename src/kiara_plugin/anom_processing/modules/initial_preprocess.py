from kiara import KiaraModule, KiaraModuleConfig, ValueMap, ValueMapSchema
from pydantic import Field
import pyarrow as pa
import ast
import re


class StringsPreprocess(KiaraModule):
    """Clean up strings that are embedded in array.

    """

   # _config_cls = ExampleModuleConfig
    _module_type_name = "anom_processing.strings_preprocess"

    def create_inputs_schema(
        self,
    ) -> ValueMapSchema:

    # we would want to pass the column only instead for better performance with the table.cut_colum module,
    # but for now I leave it like that to simplify the process at this stage

        inputs = {
            "table": {"type": "table", "doc": "The table for which a column needs to be pre-processed."},
            "column_name": {"type": "string", "doc": "The name of the column that needs pre-processing."},
        }

        return inputs

    def create_outputs_schema(
        self,
    ) -> ValueMapSchema:

        outputs = {
            "preprocessed_table": {
                "type": "table",
                "doc": "The table with pre-processed column.",
            }
        }
        return outputs

    def process(self, inputs: ValueMap, outputs: ValueMap) -> None:

        table_obj = inputs.get_value_obj("table")
        column_name = inputs.get_value_obj("column_name").data

        df = table_obj.data.to_pandas()

        def remove_arr(str_content):
            if str(str_content) == 'nan':
                return float("NaN")
            else:
                rem = re.findall(r'^\[(...+)\]$',str_content)
                if len(rem) > 0:
                    return rem[0]
                else:
                    return str_content

        
        df[column_name] = df[column_name].apply(lambda x: remove_arr(x) )


        table_pa = pa.Table.from_pandas(df)
        
        outputs.set_value("preprocessed_table", table_pa)


class ColumnNameReplace(KiaraModule):
    """Replace columns names.

    """

    _module_type_name = "anom_processing.column_names_replace"

    def create_inputs_schema(
        self,
    ) -> ValueMapSchema:


        inputs = {
            "table": {"type": "table", "doc": "The table for which one or more column names need to be replaced."},
            "columns_map": {"type": "dict", "doc": "A dict mapping old cols (left) with new cols (right)."},
        }

        return inputs

    def create_outputs_schema(
        self,
    ) -> ValueMapSchema:

        outputs = {
            "table": {
                "type": "table",
                "doc": "The table with standardised column names.",
            }
        }
        return outputs

    def process(self, inputs: ValueMap, outputs: ValueMap) -> None:

        table_obj = inputs.get_value_obj("table")
        columns_map = inputs.get_value_obj("columns_map").data
        
        new_cols = columns_map.dict_data

        df = table_obj.data.to_pandas()

        df.rename(columns = new_cols, inplace = True)

        table_pa = pa.Table.from_pandas(df)
        
        outputs.set_value("table", table_pa)

class RemoveNans(KiaraModule):
    """Remove rows containing "not a number" values for a given column.

    """

    _module_type_name = "anom_processing.remove_nans"

    def create_inputs_schema(
        self,
    ) -> ValueMapSchema:


        inputs = {
            "table": {"type": "table", "doc": "The table for which all the rows containing nans need to be removed for a given column."},
            "column": {"type": "string", "doc": "The column where nans need to be removed."},
        }

        return inputs

    def create_outputs_schema(
        self,
    ) -> ValueMapSchema:

        outputs = {
            "table": {
                "type": "table",
                "doc": "The table without nans for a given column.",
            }
        }
        return outputs

    def process(self, inputs: ValueMap, outputs: ValueMap) -> None:

        table_obj = inputs.get_value_obj("table")
        col = inputs.get_value_obj("column").data

        df = table_obj.data.to_pandas()

        # this operation should probably also be done with the sql module instead

        df = df[df[col].notna()]

        table_pa = pa.Table.from_pandas(df)
        
        outputs.set_value("table", table_pa)


class CoordsCheck(KiaraModule):
    """
    This module aims at comparing two tables: one table that provides observations with a place name, and one table that 
    includes latitudes, longitudes and place names.
    A verification is performed to see if all place names of the first dataset are included in the second dataset.
    In this specific example, the first table includes several place names per row.
    At the moment the module only covers the case of the specific example dataset (several locations per row),
    this should be improved in the future.
    """

    _module_type_name = "anom_processing.coords_check"

    def create_inputs_schema(
        self,
    ) -> ValueMapSchema:


        inputs = {
            "table1": {"type": "table", "doc": "The table that contains the observations."},
            "table2": {"type": "table", "doc": "The table that contains latitude and longitude information."},
            "column1": {"type": "string", "doc": "The column that contains the place names in table 1."},
            "column2": {"type": "string", "doc": "The column that contains the place names in table 2."},
            "sample_nr": {"type": "integer", "doc": "Number of observations to include. As this operation is very intensive it is advised to use a sample."},
        }

        return inputs

    def create_outputs_schema(
        self,
    ) -> ValueMapSchema:

        outputs = {
            "result": {
                "type": "string",
                "doc": "Information about the result (all coords present or missing coords).",
            },
            "places_list": {
                "type": "list",
                "doc": "List of the place names that are not included.",
            }
        }
        return outputs

    def process(self, inputs: ValueMap, outputs: ValueMap) -> None:

        table_obj1 = inputs.get_value_obj("table1")
        table_obj2 = inputs.get_value_obj("table2")

        col1 = inputs.get_value_obj("column1").data
        col2 = inputs.get_value_obj("column2").data

        num_sample = inputs.get_value_obj("sample_nr").data

        df1 = table_obj1.data.to_pandas()
        df1 = df1.sample(n=num_sample, random_state=1)
        df2 = table_obj2.data.to_pandas()


        col_loc = df1.columns.get_loc(col1)
        
        places = []

        for index, row in enumerate(df1.itertuples(index=False)):
            #this is not very elegant but no time to make it right
            item = re.sub(r"^'",'"',row[col_loc])
            item = re.sub(r"'$",'"',item)
            try:
                ls = ast.literal_eval(item)
                for place in ls:
                    if place not in places:
                        places.append(place)
            except:
                print(f"{item} not evaluated")
                                

        not_found_ls = [item for item in places if item not in list(df2[col2])]

        res = "All coordinates were found." if len(not_found_ls) == 0 else "Missing coordinates."

        outputs.set_value("result", res)
        outputs.set_value("places_list", not_found_ls)
