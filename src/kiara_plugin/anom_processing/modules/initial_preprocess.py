from kiara import KiaraModule, KiaraModuleConfig, ValueMap, ValueMapSchema
from pydantic import Field
import pyarrow as pa

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
            if type(str_content) == str:
                ls = eval(str_content)
                return ls
            else:
                return float("NaN")
        
        df[column_name] = df[column_name].apply(lambda x: remove_arr(x) )

        table_pa = pa.Table.from_pandas(df)
        
        outputs.set_value("preprocessed_table", table_pa)
