import pytest
import logging

import xml.etree.ElementTree as ET

from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement

from pytmc import TmcFile, PvPackage
from pytmc.xml_collector import ElementCollector

from collections import defaultdict, OrderedDict as odict

logger = logging.getLogger(__name__)

# ElementCollector tests

def test_ElementCollector_instantiation(generic_tmc_root):
    try:
        col = ElementCollector()
    except Error as e:
        pytest.fail(
            "Instantiation of XmlObjCollector should not generate errors"
        )


def test_ElementCollector_add(generic_tmc_root):
    root = generic_tmc_root
    iterator = DataType(root.find("./DataTypes/DataType/[Name='iterator']"))
    version = DataType(root.find("./DataTypes/DataType/[Name='VERSION']"))
    col = ElementCollector()
    col.add(iterator)
    col.add(version)
    assert 'iterator' in col
    assert 'VERSION' in col

    col.add(version)
    assert len(col) == 2

    assert col['iterator'] == iterator
    assert col['VERSION'] == version


def test_ElementCollector_registered(generic_tmc_root):
    root = generic_tmc_root
    iterator = DataType(root.find("./DataTypes/DataType/[Name='iterator']"))

    version = DataType(root.find("./DataTypes/DataType/[Name='VERSION']"))
    col = ElementCollector()

    col.add(iterator)
    col.add(version)

    assert col.registered == {'iterator': iterator}


# TmcFile tests

def test_TmcFile_instantiation(generic_tmc_path, generic_tmc_root):
    try:
        tmc = TmcFile(generic_tmc_path)
    except Error as e:
        pytest.fail("Instantiation of TmcFile should not generate errors")


def test_TmcFile_isolate_Symbols(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_Symbols()

    assert "MAIN.ulimit" in tmc.all_Symbols
    assert "MAIN.count" in tmc.all_Symbols
    assert "MAIN.NEW_VAR" in tmc.all_Symbols
    assert "MAIN.test_iterator" in tmc.all_Symbols
    assert "Constants.RuntimeVersion" in tmc.all_Symbols
    for x in tmc.all_Symbols:
        print(x)
    assert len(tmc.all_Symbols) == 25


def test_TmcFile_isolate_DataTypes(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_DataTypes()

    assert "iterator" in tmc.all_DataTypes
    assert "VERSION" in tmc.all_DataTypes

    assert len(tmc.all_DataTypes) == 11


def test_TmcFile_isolate_SubItems(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_DataTypes(process_subitems=False)
    tmc.isolate_SubItems('iterator')

    assert 'increment' in tmc.all_SubItems['iterator']
    assert 'out' in tmc.all_SubItems['iterator']
    assert 'value' in tmc.all_SubItems['iterator']
    assert 'lim' in tmc.all_SubItems['iterator']
    assert 'extra1' in tmc.all_SubItems['iterator']
    assert 'extra2' in tmc.all_SubItems['iterator']
   
    assert len(tmc.all_SubItems['iterator']) == 6


def test_TmcFile_isolate_all(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_all()
    
    assert "MAIN.ulimit" in tmc.all_Symbols
    assert "MAIN.count" in tmc.all_Symbols
    assert "MAIN.NEW_VAR" in tmc.all_Symbols
    assert "MAIN.test_iterator" in tmc.all_Symbols
    assert "Constants.RuntimeVersion" in tmc.all_Symbols

    assert len(tmc.all_Symbols) == 25


    assert "iterator" in tmc.all_DataTypes
    assert "VERSION" in tmc.all_DataTypes
    
    assert len(tmc.all_DataTypes) == 11

    assert 'increment' in tmc.all_SubItems['iterator']
    assert 'out' in tmc.all_SubItems['iterator']
    assert 'value' in tmc.all_SubItems['iterator']
    assert 'lim' in tmc.all_SubItems['iterator']
    assert 'extra1' in tmc.all_SubItems['iterator']
    assert 'extra2' in tmc.all_SubItems['iterator']
   
    assert len(tmc.all_SubItems['iterator']) == 6


# PvPackage tests

def test_PvPackage_instantiation(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    #print(tmc.all_Symbols)
    #print(tmc.all_DataTypes)
    #print(tmc.all_SubItems)
    element_path = [
        tmc.all_Symbols['MAIN.test_iterator'],
        tmc.all_SubItems['iterator']['value']
    ]
    
    # ensure that you can instantiate w/o errors
    try:
        pv_pack = PvPackage(
            target_path = element_path,
            pragma = element_path[-1].config_by_pv()[0],
            proto_name = '',
            proto_file_name = '',
        )
    except:
        pytest.fail()

    # ensure that the pragmas properly crossed over
    #print(tmc.all_SubItems['iterator']['value'].config_by_pv)
    assert pv_pack.pv_complete == "TEST:MAIN:ITERATOR:VALUE"
    assert {'title':'pv', 'tag':'VALUE'} in pv_pack.pragma


def test_PvPackage_assemble_package_chains(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    paths = PvPackage.assemble_package_chains(element_path)
    assert paths == [
        [tmc.all_Symbols['MAIN.NEW_VAR'].filter_by_pv('TEST:MAIN:NEW_VAR_IN')],
        [tmc.all_Symbols['MAIN.NEW_VAR'].filter_by_pv('TEST:MAIN:NEW_VAR_OUT')]
    ]
    
    
    element_path = [
        tmc.all_Symbols['MAIN.dtype_samples_iter_array'],
    ]
    paths = PvPackage.assemble_package_chains(element_path)
    assert paths == [
        [
            tmc.all_Symbols['MAIN.dtype_samples_iter_array'].flter_by_pv(
                'TEST:MAIN:VAR_ARRAY'+str(n)
            )
        ] for n in range(1,5)
    ]
    
    element_path = [
        tmc.all_Symbols['MAIN.struct_base'],
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
    ]
    paths = PvPackage.assemble_package_chains(element_path)
    assert paths == [
        [
            tmc.all_Symbols['MAIN.struct_base'].flter_by_pv(
                'TEST:MAIN:STRUCTBASE'
            ),
            tmc.all_SubItems['DUT_STRUCT']['struct_var'].flter_by_pv(
                'TEST:MAIN:STRUCTBASE:STRUCT_VAR'
            ),
        ]
    ]
    

def test_PvPackage_from_element_path(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    # test the creation of a normal multi-pv variable  
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs, rejects = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
        return_rejects = True
    )
    logging.debug("pv_packs: " + str(pv_packs))
    logging.debug("rejects: " + str(rejects))

    assert len(pv_packs) == 2
    assert len(rejects) == 0

    assert pv_packs[0].guessing_applied == False
    assert pv_packs[1].guessing_applied == False

    assert pv_packs[0].pv_partial == "TEST:MAIN:NEW_VAR_OUT"
    assert pv_packs[1].pv_partial == "TEST:MAIN:NEW_VAR_IN"

    assert pv_packs[0].pv_complete == "TEST:MAIN:NEW_VAR_OUT"
    assert pv_packs[1].pv_complete == "TEST:MAIN:NEW_VAR_IN"

    assert pv_packs[0].proto_name == "SetNEW_VAR"
    assert pv_packs[1].proto_name == "GetNEW_VAR"
    
    # test the creation of an array of user-defined type
    element_path = [
        tmc.all_Symbols['MAIN.dtype_samples_iter_array'],
    ]
    pv_packs, rejects = PvPackage.from_element_path(
        target_path = element_path,
        return_rejects = True
    )
    logging.debug("pv_packs: " + str(pv_packs))
    logging.debug("rejects: " + str(rejects))
    
    assert len(pv_packs) == 0
    assert len(rejects) == 1
    assert rejects[0].pv_partial == "TEST:MAIN:VAR_ARRAY[]"
    assert rejects[0].pv_complete == "TEST:MAIN:VAR_ARRAY[]"
    assert rejects[0].proto_name == None

    # test the creation of an encapsulated 
    element_path = [
        tmc.all_Symbols['MAIN.struct_base'],
        tmc.all_SubItems['struct_var'],
    ]
    pv_packs, rejects = PvPackage.from_element_path(
        target_path = element_path,
        return_rejects = True
    )
    logging.debug("pv_packs: " + str(pv_packs))
    logging.debug("rejects: " + str(rejects))
    assert len(pv_packs) == 1
    assert len(rejects) == 0
    assert rejects[0].pv_partial == "STRUCT_VAR"
    assert rejects[0].pv_complete == "TEST:MAIN:STRUCT_BASE"


def test_PvPackage_make_config(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    new = pv_out.make_config(title="test_line", setting="test", field=False)
    assert {'title': 'test_line', 'tag': 'test'} == new 

    new = pv_out.make_config(title="FLD", setting="test 9", field=True)
    assert {
        'title': 'field',
        'tag': {'f_name': "FLD", 'f_set': 'test 9'}
    } == new 


def test_PvPackage_missing_pragma_lines(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    ''' 
    for x in pv_out.pragma:
        print(x)
    '''
    missing = pv_out.missing_pragma_lines()
    
    assert odict([('field',['title']),('DTYP',['tag','f_name'])]) in missing
    assert odict([('field',['title']),('INP',['tag','f_name'])]) in missing
    
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'DTYP', 'f_set': ''}}
    )
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'INP', 'f_set': ''}}
    )
    
    assert [] == pv_out.missing_pragma_lines()


def test_PvPackage_is_config_complete(generic_tmc_path):
    '''Test a single version for pragma completeness. This only tests for the
    existance of these fields, it does NOT test if they are valid.
    '''
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    '''
    for x in pv_out.pragma:
        print(x)
    '''

    assert False == pv_out.is_config_complete
    
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'DTYP', 'f_set': ''}}
    )
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'INP', 'f_set': ''}}
    )
    
    assert True == pv_out.is_config_complete


def test_PvPackage_term_exists(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, _ = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )

    # confirm that the 'pv' field exists, rule 0
    assert pv_out.term_exists(pv_out.req_fields[0]) == True
    # confirm that the 'INP field does not exist, rule 6
    assert pv_out.term_exists(pv_out.req_fields[6]) == False


def test_PvPackage_eq(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    assert pv_out == pv_out
    assert pv_out != pv_in 

# PvPackage field guessing tests






@pytest.mark.skip(reason="Incomplete")
def test_PvPackage_guess():
    ''
    assert pv_packs[0].fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }
    assert pv_packs[1].fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }


@pytest.mark.skip(reason="Pending development of feature guessing")
def test_PvPackage_create_record(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
        use_proto = True,
    )

    print(element_path)
    record0 = pv_packs[0].create_record()
    assert record0.pv == "TEST:MAIN:NEW_VAR_OUT"
    assert record0.rec_type == "bo"
    assert record0.fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }
    assert record0.comment


@pytest.mark.skip(reason="Pending development of feature guessing")
def test_PvPackage_create_proto(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
        use_proto = True,
    )

    proto0 = pv_packs[0].create_proto()
    '''
    assert proto0.name
    assert proto0.out_field
    assert proto0.in_field
    assert proto0.init
    '''

